using System;
using System.Collections.Generic;
using System.Threading.Tasks;

namespace Ramses.Server.Domain;

public interface IDeviceRepository
{
    Task<Device?> GetByIdAsync(Guid id);
    Task<IEnumerable<Device>> GetAllAsync();
    Task AddAsync(Device device);
    Task UpdateAsync(Device device);
    Task DeleteAsync(Guid id);
}

public interface IAgentConnector
{
    Task SendInstructionAsync(Guid deviceId, Instruction instruction);
    Task BroadcastStatusAsync(DeviceStatusReport report);
}

public interface ILicenseService
{
    LicenseInfo GetLicenseStatus();
    bool CanAddDevice();
    void IncrementInstanceCount();
}

public interface IInstructionParser
{
    // For future parsing of .md instructions into device-specific commands
    // e.g. for Cardputer, ESP32-S3, watches
    Task<Dictionary<string, object>> ParseMarkdownToCommandsAsync(string markdown);
}
