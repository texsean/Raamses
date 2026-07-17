using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;
using Ramses.Server.Domain;

namespace Ramses.Server.Infrastructure;

public class LoggingAgentConnector : IAgentConnector
{
    private readonly ILogger<LoggingAgentConnector> _logger;
    private readonly IInstructionParser _parser;

    public LoggingAgentConnector(ILogger<LoggingAgentConnector> logger, IInstructionParser parser)
    {
        _logger = logger;
        _parser = parser;
    }

    public async Task SendInstructionAsync(Guid deviceId, Instruction instruction)
    {
        var commands = await _parser.ParseMarkdownToCommandsAsync(instruction.MarkdownContent);
        _logger.LogInformation("📡 [RAMSES] Sending instruction to device {DeviceId}. Bond would be proud.\nMD: {Markdown}\nParsed commands: {Count}", 
            deviceId, 
            instruction.MarkdownContent.Substring(0, Math.Min(100, instruction.MarkdownContent.Length)),
            commands.Count);
        
        // In real impl, would route to specific client (Cardputer via BLE? ESP32 via MQTT, Watch via WebSocket)
        instruction.Executed = true;
        instruction.Result = "Emulated execution successful. Shaken, not stirred.";
    }

    public Task BroadcastStatusAsync(DeviceStatusReport report)
    {
        _logger.LogInformation("📊 [RAMSES STATUS] Device {DeviceId} reports: {Status} at {Time}. Virtual client emulator active.", 
            report.DeviceId, report.Status, report.Timestamp);
        return Task.CompletedTask;
    }
}

public class BasicInstructionParser : IInstructionParser
{
    public Task<Dictionary<string, object>> ParseMarkdownToCommandsAsync(string markdown)
    {
        // Simple parser stub for extensibility
        var commands = new Dictionary<string, object>();
        if (!string.IsNullOrEmpty(markdown))
        {
            commands["action"] = markdown.Contains("#") ? "execute" : "status";
            commands["target"] = "device";
            commands["parsed_from_md"] = true;
            // Future: advanced parsing for different clients e.g. Cardputer buttons, ESP32 GPIO, watch UI
        }
        return Task.FromResult(commands);
    }
}
