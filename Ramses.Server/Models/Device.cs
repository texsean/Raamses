using System.Text.Json.Serialization;

namespace Ramses.Server.Models;

/// <summary>
/// Represents a registered device with MAC-based ID and activity tracking.
/// Focus on one-device-free-tier rule.
/// </summary>
public class Device
{
    [JsonPropertyName("id")]
    public string Id { get; set; } = string.Empty; // MD5 hash of MAC address

    [JsonPropertyName("macAddress")]
    public string MacAddress { get; set; } = string.Empty;

    [JsonPropertyName("registeredAt")]
    public DateTime RegisteredAt { get; set; } = DateTime.UtcNow;

    [JsonPropertyName("lastActive")]
    public DateTime LastActive { get; set; } = DateTime.UtcNow;

    [JsonPropertyName("isActive")]
    public bool IsActive => (DateTime.UtcNow - LastActive).TotalMinutes < 15; // Configurable timeout

    public void UpdateActivity()
    {
        LastActive = DateTime.UtcNow;
    }
}
