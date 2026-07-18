using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Net.Http.Json;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;
using Ramses.Server.Application;
using Ramses.Server.Domain;

namespace Ramses.Server.Api.Services;

/// <summary>
/// Virtual client emulator for testing different device clients (Cardputer, ESP32-S3, watches).
/// Simulates sending status reports with .md instructions to the Ramses server API.
/// Extensible for future hardware-specific emulation.
/// </summary>
public class VirtualClientEmulatorService
{
    private readonly HttpClient _httpClient;
    private readonly ILogger<VirtualClientEmulatorService> _logger;
    private readonly DeviceService _deviceService;
    private bool _isRunning = false;

    public VirtualClientEmulatorService(HttpClient httpClient, ILogger<VirtualClientEmulatorService> logger, DeviceService deviceService)
    {
        _httpClient = httpClient;
        _logger = logger;
        _deviceService = deviceService;
    }

    public async Task StartEmulatorAsync(Guid deviceId, DeviceType type, string deviceName)
    {
        if (_isRunning) return;
        _isRunning = true;

        _logger.LogInformation("🚀 Starting Virtual {Type} Emulator for {Name} (Ramses / James Bond Mode Activated)", type, deviceName);

        // Simulate periodic status updates and MD instruction flow
        while (_isRunning)
        {
            try
            {
                var report = new DeviceStatusReport
                {
                    DeviceId = deviceId,
                    Status = "Online - Emulated",
                    Details = $"Virtual {type} client running. Battery: 87%. Signal: Excellent. Awaiting orders.",
                    MarkdownInstruction = "# Mission Briefing\n- **Objective**: Monitor target\n- **Action**: Report anomalies via MD\n**Agent Status**: All systems nominal."
                };

                // Send to the API endpoint
                var response = await _httpClient.PostAsJsonAsync("/api/status", report);
                if (response.IsSuccessStatusCode)
                {
                    _logger.LogInformation("✅ [RAMSES] Emulator status sent and acknowledged by server.");
                }

                await Task.Delay(15000); // Simulate real device polling interval
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Emulator encountered issue. Mission may be compromised.");
                await Task.Delay(5000);
            }
        }
    }

    public void Stop()
    {
        _isRunning = false;
        _logger.LogInformation("🛑 Virtual Client Emulator stopped. Debriefing complete.");
    }

    public string GetEmulatorStatus() => _isRunning ? "Active - Operating with license to thrill" : "Standby";
}
