using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Ramses.Server.Application;
using Ramses.Server.Domain;
using Ramses.Server.Infrastructure;
using Ramses.Server.Api.Components;
using Ramses.Server.Api.Services;

var builder = WebApplication.CreateBuilder(args);

// Add services to the container.
builder.Services.AddRazorComponents()
    .AddInteractiveServerComponents();

// Clean Architecture + Dependency Injection for extensibility (easy to add Cardputer, ESP32-S3, watch connectors)
builder.Services.AddSingleton<IDeviceRepository, InMemoryDeviceRepository>();
builder.Services.AddSingleton<ILicenseService, StubLicenseService>();
builder.Services.AddSingleton<IInstructionParser, BasicInstructionParser>();
builder.Services.AddSingleton<IAgentConnector, LoggingAgentConnector>();
builder.Services.AddSingleton<DeviceService>();

// Virtual emulator
builder.Services.AddScoped<VirtualClientEmulatorService>();

// Logging (spy-themed console output)
builder.Logging.AddConsole();
builder.Services.AddLogging(logging => logging.SetMinimumLevel(LogLevel.Information));

// HTTP client for emulator
builder.Services.AddHttpClient();

var app = builder.Build();

// Configure the HTTP request pipeline.
if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error", createScopeForErrors: true);
}

app.UseStaticFiles();
app.UseAntiforgery();

// Core API endpoints: Agents send status + .md instructions to central Ramses server (no direct device calls)
app.MapPost("/api/status", async (DeviceStatusReport report, DeviceService service) =>
{
    await service.UpdateDeviceStatusAsync(report);
    return Results.Ok(new { success = true, message = "Status received by Ramses Server. 007 approves." });
})
.WithTags("Ramses Agents");

app.MapPost("/api/instructions", async (SendInstructionRequest request, DeviceService service) =>
{
    await service.SendInstructionAsync(request.DeviceId, request.Markdown);
    return Results.Ok(new { success = true, message = "Markdown instruction delivered. For your eyes only." });
})
.WithTags("Ramses Agents");

app.MapRazorComponents<App>()
    .AddInteractiveServerRenderMode();

app.Run();

// DTO for clean API
public record SendInstructionRequest(Guid DeviceId, string Markdown);
