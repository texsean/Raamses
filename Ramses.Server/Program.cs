using System;
using System.Collections.Generic;
using System.Net;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.IO;

namespace Ramses.Server
{
    class Program
    {
        private static readonly string DbPath = "ramses_devices.json";
        private static Dictionary<string, DeviceRecord> devices = new();
        private static readonly object lockObj = new object();
        private static Timer statsTimer;

        static void Main(string[] args)
        {
            Console.WriteLine("Ramses Server starting...");

            LoadDatabase();

            // Start background stats update
            statsTimer = new Timer(UpdateMockStats, null, 0, 8000);

            // Start HTTP listener on port 8080
            var listener = new HttpListener();
            listener.Prefixes.Add("http://+:8080/");
            listener.Start();
            Console.WriteLine("Listening on http://localhost:8080");

            while (true)
            {
                var context = listener.GetContext();
                ThreadPool.QueueUserWorkItem(HandleRequest, context);
            }
        }

        private static void HandleRequest(object state)
        {
            var context = (HttpListenerContext)state;
            var request = context.Request;
            var response = context.Response;

            try
            {
                if (request.Url.AbsolutePath == "/stats")
                {
                    var stats = GetCurrentStats();
                    var json = JsonSerializer.Serialize(stats, new JsonSerializerOptions { WriteIndented = true });
                    var buffer = Encoding.UTF8.GetBytes(json);

                    response.ContentType = "application/json";
                    response.ContentLength64 = buffer.Length;
                    response.OutputStream.Write(buffer, 0, buffer.Length);
                }
                else if (request.Url.AbsolutePath == "/register")
                {
                    // Registration logic (MAC -> deviceId)
                    var mac = request.QueryString["mac"] ?? "unknown";
                    var deviceId = ComputeMD5(mac);
                    RegisterDevice(deviceId, mac);
                    var reply = new { status = "registered", deviceId = deviceId };
                    var json = JsonSerializer.Serialize(reply);
                    var buffer = Encoding.UTF8.GetBytes(json);
                    response.ContentType = "application/json";
                    response.OutputStream.Write(buffer, 0, buffer.Length);
                }
                else
                {
                    response.StatusCode = 404;
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine("Error: " + ex.Message);
                response.StatusCode = 500;
            }
            response.Close();
        }

        private static void RegisterDevice(string deviceId, string mac)
        {
            lock (lockObj)
            {
                if (!devices.ContainsKey(deviceId))
                {
                    devices[deviceId] = new DeviceRecord { Mac = mac, LastSeen = DateTime.UtcNow, IsActive = true };
                    SaveDatabase();
                    Console.WriteLine($"Device registered: {deviceId}");
                }
                else
                {
                    devices[deviceId].LastSeen = DateTime.UtcNow;
                    devices[deviceId].IsActive = true;
                }
            }
        }

        private static object GetCurrentStats()
        {
            lock (lockObj)
            {
                // Pull some real system stats where possible
                var cpu = (int)(new PerformanceCounter("Processor", "% Processor Time", "_Total").NextValue());
                var mem = (int)((1 - (double)GC.GetGCMemoryInfo().AvailableMemory / Environment.WorkingSet) * 100);

                return new
                {
                    agents = 4,
                    subagents = 9,
                    tokens_used = 18420,
                    tokens_limit = 25000,
                    tokens_last_hour = 3240,
                    tokens_today = 8740,
                    sprint_status = "Sprint 4 of 7 - Final Review",
                    last_alert = "Server 2 requesting permission (2 min ago)",
                    overall_status = "green",
                    cpu_usage = cpu + "%",
                    memory_usage = mem + "%",
                    timestamp = DateTime.UtcNow.ToString("o"),
                    // Summary vs Full Data for different device sizes
                    summary = new { agents = 4, tokens = "18.4k/25k", status = "green" },
                    fulldata = new { 
                        agents = 4, 
                        subagents = 9, 
                        tokens_used = 18420, 
                        tokens_today = 8740, 
                        tokens_last_hour = 3240,
                        sprint = "Sprint 4 of 7",
                        last_alert = "Server 2 requesting permission (2 min ago)",
                        cpu = cpu + "%",
                        memory = mem + "%"
                    }
                };
            }
        }

        private static void UpdateMockStats(object state)
        {
            Console.WriteLine("Stats update thread started...");
            // In real version this would read from actual agent processes or logs
        }

        private static string ComputeMD5(string input)
        {
            using (var md5 = System.Security.Cryptography.MD5.Create())
            {
                var hash = md5.ComputeHash(Encoding.UTF8.GetBytes(input));
                return BitConverter.ToString(hash).Replace("-", "").ToLower();
            }
        }

        private static void LoadDatabase()
        {
            if (File.Exists(DbPath))
            {
                var json = File.ReadAllText(DbPath);
                devices = JsonSerializer.Deserialize<Dictionary<string, DeviceRecord>>(json) ?? new();
            }
        }

        private static void SaveDatabase()
        {
            var json = JsonSerializer.Serialize(devices, new JsonSerializerOptions { WriteIndented = true });
            File.WriteAllText(DbPath, json);
        }
    }

    public class DeviceRecord
    {
        public string Mac { get; set; }
        public DateTime LastSeen { get; set; }
        public bool IsActive { get; set; }
    }
}
