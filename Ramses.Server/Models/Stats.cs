using System.Text.Json.Serialization;

namespace Ramses.Server.Models;

/// <summary>
/// Rich stats for the Ramses system. Includes agent metrics, token usage, 
/// system resources, and status for the color-coded status bar.
/// </summary>
public class Stats
{
    [JsonPropertyName("agents")]
    public int Agents { get; set; } = 3;

    [JsonPropertyName("subagents")]
    public int Subagents { get; set; } = 12;

    [JsonPropertyName("tokens")]
    public TokenUsage Tokens { get; set; } = new();

    [JsonPropertyName("sprintStatus")]
    public string SprintStatus { get; set; } = "In Progress";

    [JsonPropertyName("lastAlert")]
    public string LastAlert { get; set; } = "None";

    [JsonPropertyName("cpuUsage")]
    public double CpuUsage { get; set; } = 45.2;

    [JsonPropertyName("memoryUsage")]
    public double MemoryUsage { get; set; } = 62.5;

    [JsonPropertyName("status")]
    public string Status { get; set; } = "green"; // green, yellow, orange, red

    [JsonPropertyName("statusColor")]
    public string StatusColor { get; set; } = "#00FF00";

    [JsonPropertyName("registeredDevices")]
    public int RegisteredDevices { get; set; } = 0;

    [JsonPropertyName("freeSlots")]
    public int FreeSlots { get; set; } = 1;
}

public class TokenUsage
{
    [JsonPropertyName("today")]
    public int Today { get; set; } = 125000;

    [JsonPropertyName("lastHour")]
    public int LastHour { get; set; } = 45000;

    [JsonPropertyName("total")]
    public long Total { get; set; } = 2450000;

    [JsonPropertyName("percentUsed")]
    public double PercentUsed { get; set; } = 45.0;
}
