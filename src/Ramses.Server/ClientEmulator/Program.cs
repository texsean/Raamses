using System;
using System.Net.Http;
using System.Net.Http.Json;
using System.Text.Json;
using Ramses.Server.Domain;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;

namespace Ramses.Server.ClientEmulator;

class Program
{
    static async Task Main(string[] args)
    {
        Console.WriteLine("========================================");
        Console.WriteLine("RAMSES VIRTUAL CLIENT EMULATOR");
        Console.WriteLine("James Bond Edition - Licensed to Simulate");
        Console.WriteLine("Supports future: Cardputer, ESP32-S3, Smart Watches");
        Console.WriteLine("========================================");
        Console.WriteLine("This emulator sends status reports and receives .md instructions via the Ramses Server API.");
        Console.WriteLine();

        var services = new ServiceCollection();
        services.AddHttpClient();
        services.AddLogging(builder => builder.AddConsole().SetMinimumLevel(LogLevel.Information));
        using var serviceProvider = services.BuildServiceProvider();

        var httpClient = serviceProvider.GetRequiredService<HttpClient>();
        var logger = serviceProvider.GetRequiredService<ILogger<Program>>();

        httpClient.BaseAddress = new Uri("http://localhost:8080"); // Default Blazor port, update if changed

        var deviceId = Guid.NewGuid();
        var emulator = new VirtualClientEmulator(httpClient, logger, deviceId);

        Console.WriteLine("Starting emulator... Press Ctrl+C to stop.");
        await emulator.RunAsync();

        Console.WriteLine("Emulator terminated. Mission complete.");
    }
}

public class VirtualClientEmulator
{
    private readonly HttpClient _client;
    private readonly ILogger _logger;
    private readonly Guid _deviceId;
    private bool _running = true;

    public VirtualClientEmulator(HttpClient client, ILogger logger, Guid deviceId)
    {
        _client = client;
        _logger = logger;
        _deviceId = deviceId;
    }

    public async Task RunAsync()
    {
        var random = new Random();
        while (_running)
        {
            try
            {
                var report = new DeviceStatusReport
                {
                    DeviceId = _deviceId,
                    Status = random.Next(0, 2) == 0 ? "Online" : "Idle",
                    Details = "Virtual client active. Ready for MD instructions from Ramses central.",
                    MarkdownInstruction = "## Field Report\n- Location: Secure\n- **Threat Level**: Low\n> \"The world is not enough\" - Q"
                };

                var response = await _client.PostAsJsonAsync("/api/status", report);
                if (response.IsSuccessStatusCode)
                {
                    _logger.LogInformation("Status sent successfully from virtual client {Id}. Server received MD payload.", _deviceId);
                }
                else
                {
                    _logger.LogWarning("Server not responding. Is Ramses Server running?");
                }

                await Task.Delay(8000);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Connection to Ramses Server failed. Check if API is up on port 8080.");
                await Task.Delay(10000);
            }
        }
    }
}
