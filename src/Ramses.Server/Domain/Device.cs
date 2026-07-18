using System;

namespace Ramses.Server.Domain;

public enum DeviceType
{
    Virtual,
    Cardputer,
    Esp32S3,
    SmartWatch
}

public class Device
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public string Name { get; set; } = string.Empty;
    public DeviceType Type { get; set; }
    public string Status { get; set; } = "Offline";
    public DateTime LastSeen { get; set; } = DateTime.UtcNow;
    public string ConfigJson { get; set; } = "{}";
    public string ConnectionId { get; set; } = string.Empty; // For WebSocket or similar
}

public class DeviceStatusReport
{
    public Guid DeviceId { get; set; }
    public string Status { get; set; } = string.Empty;
    public string Details { get; set; } = string.Empty;
    public DateTime Timestamp { get; set; } = DateTime.UtcNow;
    public string MarkdownInstruction { get; set; } = string.Empty; // Agents send MD instructions via server
}

public class Instruction
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public Guid DeviceId { get; set; }
    public string MarkdownContent { get; set; } = string.Empty;
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public bool Executed { get; set; }
    public string Result { get; set; } = string.Empty;
}

public class LicenseInfo
{
    public bool IsLicensed { get; set; }
    public int MaxFreeInstances { get; set; } = 1;
    public int CurrentInstances { get; set; }
    public string Message { get; set; } = "Ramses Server - Licensed to Sean. Free for 1 instance. James Bond would approve.";
}
