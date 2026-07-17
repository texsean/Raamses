using System;
using Ramses.Server.Domain;

namespace Ramses.Server.Infrastructure;

public class StubLicenseService : ILicenseService
{
    private int _currentInstances = 0;
    private const int MAX_FREE = 1;

    public LicenseInfo GetLicenseStatus()
    {
        return new LicenseInfo
        {
            IsLicensed = _currentInstances <= MAX_FREE,
            MaxFreeInstances = MAX_FREE,
            CurrentInstances = _currentInstances,
            Message = "Ramses Server v0.1 - James Bond Edition. \"The name's Ramses... Licensed to Deploy.\" Free tier: 1 instance. Upgrade for more devices (Cardputer, ESP32-S3, watches)."
        };
    }

    public bool CanAddDevice()
    {
        return _currentInstances < MAX_FREE;
    }

    public void IncrementInstanceCount()
    {
        _currentInstances++;
    }
}
