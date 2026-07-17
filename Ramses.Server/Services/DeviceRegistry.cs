using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Ramses.Server.Models;

namespace Ramses.Server.Services;

/// <summary>
/// Manages device registration using MD5 hash of MAC address.
/// Enforces max 1 free device rule and 15-minute inactivity timeout.
/// Uses simple JSON flat-file database for persistence.
/// Easy to extend to real DB later.
/// </summary>
public class DeviceRegistry
{
    private readonly string _dbPath;
    private readonly int _maxFreeDevices;
    private readonly int _inactivityTimeoutMinutes;
    private List<Device> _devices = new();
    private readonly object _lock = new();

    public DeviceRegistry(string dbPath = "devices.json", int maxFreeDevices = 1, int inactivityTimeoutMinutes = 15)
    {
        _dbPath = dbPath;
        _maxFreeDevices = maxFreeDevices;
        _inactivityTimeoutMinutes = inactivityTimeoutMinutes;
        LoadDevices();
        
        // Start cleanup timer for inactivity
        _ = Task.Run(async () =>
        {
            while (true)
            {
                await Task.Delay(TimeSpan.FromMinutes(5));
                CleanupInactiveDevices();
            }
        });
    }

    private void LoadDevices()
    {
        if (File.Exists(_dbPath))
        {
            try
            {
                var json = File.ReadAllText(_dbPath);
                _devices = JsonSerializer.Deserialize<List<Device>>(json) ?? new List<Device>();
                Console.WriteLine($"Loaded {_devices.Count} registered devices from database.");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error loading devices: {ex.Message}. Starting fresh.");
                _devices = new List<Device>();
            }
        }
        else
        {
            Console.WriteLine("No device database found. Starting with empty registry.");
            SaveDevices();
        }
    }

    private void SaveDevices()
    {
        lock (_lock)
        {
            try
            {
                var options = new JsonSerializerOptions { WriteIndented = true };
                var json = JsonSerializer.Serialize(_devices, options);
                File.WriteAllText(_dbPath, json);
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error saving devices: {ex.Message}");
            }
        }
    }

    /// <summary>
    /// Registers a device using MD5 hash of its MAC address.
    /// Enforces the one free device limit.
    /// </summary>
    public bool RegisterDevice(string macAddress, out string deviceId)
    {
        deviceId = ComputeMd5Hash(macAddress.ToUpperInvariant().Replace(":", "").Replace("-", ""));
        
        lock (_lock)
        {
            // Check if already registered
            var existing = _devices.FirstOrDefault(d => d.Id == deviceId);
            if (existing != null)
            {
                existing.UpdateActivity();
                SaveDevices();
                return true;
            }

            // Check free slots (max 1 free device)
            CleanupInactiveDevices();
            var activeCount = _devices.Count(d => d.IsActive);
            if (activeCount >= _maxFreeDevices)
            {
                deviceId = string.Empty;
                return false; // No free slots
            }

            var device = new Device
            {
                Id = deviceId,
                MacAddress = macAddress,
                RegisteredAt = DateTime.UtcNow,
                LastActive = DateTime.UtcNow
            };

            _devices.Add(device);
            SaveDevices();
            Console.WriteLine($"Device registered: {deviceId} (MAC: {macAddress})");
            return true;
        }
    }

    public bool IsRegistered(string macAddress)
    {
        var deviceId = ComputeMd5Hash(macAddress.ToUpperInvariant().Replace(":", "").Replace("-", ""));
        lock (_lock)
        {
            CleanupInactiveDevices();
            return _devices.Any(d => d.Id == deviceId && d.IsActive);
        }
    }

    private void CleanupInactiveDevices()
    {
        lock (_lock)
        {
            var now = DateTime.UtcNow;
            var toRemove = _devices.Where(d => (now - d.LastActive).TotalMinutes > _inactivityTimeoutMinutes).ToList();
            
            if (toRemove.Count > 0)
            {
                foreach (var device in toRemove)
                {
                    Console.WriteLine($"Device timed out due to inactivity: {device.Id}");
                }
                _devices.RemoveAll(d => (now - d.LastActive).TotalMinutes > _inactivityTimeoutMinutes);
                SaveDevices();
            }
        }
    }

    private static string ComputeMd5Hash(string input)
    {
        using var md5 = MD5.Create();
        var inputBytes = Encoding.UTF8.GetBytes(input);
        var hashBytes = md5.ComputeHash(inputBytes);
        return BitConverter.ToString(hashBytes).Replace("-", "").ToLowerInvariant();
    }

    public int GetActiveDeviceCount()
    {
        lock (_lock)
        {
            CleanupInactiveDevices();
            return _devices.Count(d => d.IsActive);
        }
    }

    public List<Device> GetAllDevices()
    {
        lock (_lock)
        {
            CleanupInactiveDevices();
            return _devices.ToList();
        }
    }
}
