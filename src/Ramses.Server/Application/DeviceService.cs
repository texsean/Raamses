using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Logging.Abstractions;
using Ramses.Server.Domain;

namespace Ramses.Server.Application;

public class DeviceService
{
    private readonly IDeviceRepository _repository;
    private readonly ILicenseService _licenseService;
    private readonly IAgentConnector _connector;
    private readonly ILogger<DeviceService> _logger;

    public DeviceService(
        IDeviceRepository repository,
        ILicenseService licenseService,
        IAgentConnector connector,
        ILogger<DeviceService> logger)
    {
        _repository = repository;
        _licenseService = licenseService;
        _connector = connector;
        _logger = logger ?? NullLogger<DeviceService>.Instance;
    }

    public async Task<IEnumerable<Device>> GetAllDevicesAsync()
    {
        return await _repository.GetAllAsync();
    }

    public async Task<Device?> GetDeviceAsync(Guid id)
    {
        return await _repository.GetByIdAsync(id);
    }

    public async Task<bool> AddDeviceAsync(Device device)
    {
        if (!_licenseService.CanAddDevice())
        {
            _logger.LogWarning("License limit reached. Free for 1 instance only. (James Bond doesn't pay for extras)");
            return false;
        }

        await _repository.AddAsync(device);
        _licenseService.IncrementInstanceCount();
        _logger.LogInformation("Device {Name} ({Type}) added to Ramses network. Shaken, not stirred.", device.Name, device.Type);
        return true;
    }

    public async Task SendInstructionAsync(Guid deviceId, string markdownInstruction)
    {
        var device = await _repository.GetByIdAsync(deviceId);
        if (device == null) 
        {
            _logger.LogWarning("Device {Id} not found for instruction.", deviceId);
            return;
        }

        var instruction = new Instruction
        {
            DeviceId = deviceId,
            MarkdownContent = markdownInstruction,
            // Extensible for future Cardputer (MicroPython scripts), ESP32-S3 (Arduino/ IDF), watch clients
        };

        await _connector.SendInstructionAsync(deviceId, instruction);
        _logger.LogInformation("📋 Instruction sent to {Device}. MD length: {Len} chars. For your eyes only.", device.Name, markdownInstruction.Length);
    }

    public async Task UpdateDeviceStatusAsync(DeviceStatusReport report)
    {
        var device = await _repository.GetByIdAsync(report.DeviceId);
        if (device != null)
        {
            device.Status = report.Status;
            device.LastSeen = report.Timestamp;
            await _repository.UpdateAsync(device);
            await _connector.BroadcastStatusAsync(report);
            _logger.LogInformation("📡 Status updated for {Id}: {Status} - Virtual emulator synced.", report.DeviceId, report.Status);
        }
    }
}
