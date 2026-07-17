using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Ramses.Server.Domain;

namespace Ramses.Server.Infrastructure;

public class InMemoryDeviceRepository : IDeviceRepository
{
    private readonly List<Device> _devices = new();

    public Task<Device?> GetByIdAsync(Guid id)
    {
        var device = _devices.FirstOrDefault(d => d.Id == id);
        return Task.FromResult(device);
    }

    public Task<IEnumerable<Device>> GetAllAsync()
    {
        return Task.FromResult(_devices.AsEnumerable());
    }

    public Task AddAsync(Device device)
    {
        _devices.Add(device);
        return Task.CompletedTask;
    }

    public Task UpdateAsync(Device device)
    {
        var existing = _devices.FirstOrDefault(d => d.Id == device.Id);
        if (existing != null)
        {
            var index = _devices.IndexOf(existing);
            _devices[index] = device;
        }
        return Task.CompletedTask;
    }

    public Task DeleteAsync(Guid id)
    {
        var device = _devices.FirstOrDefault(d => d.Id == id);
        if (device != null)
        {
            _devices.Remove(device);
        }
        return Task.CompletedTask;
    }
}
