#include <Arduino.h>
#include <WiFi.h>
#include <WiFiManager.h>
#include <ESPAsyncWebServer.h>
#include <TFT_eSPI.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <LittleFS.h>

TFT_eSPI tft = TFT_eSPI();
AsyncWebServer server(8080);

String deviceName = "Ramses Monitor";
int currentPage = 1;  // 1 = Agent Status, 2 = Basic Info, 3 = RSS Reader

// Sample data (will be updated from API)
int agents = 3;
int subagents = 2;
float projectProgress = 63.0;
String currentPrompt = "Waiting for approval...";
String sprintStatus = "Sprint 4 (Final)";

void displayPage1() {  // AI Agent Status - Main Dashboard
    tft.fillScreen(TFT_BLACK);
    tft.setTextColor(TFT_CYAN, TFT_BLACK);
    tft.setTextSize(3);
    tft.setCursor(10, 10);
    tft.println(deviceName);

    tft.setTextSize(2);
    tft.setTextColor(TFT_WHITE);
    tft.setCursor(10, 60);
    tft.printf("Agents: %d  Sub: %d\n", agents, subagents);
    tft.printf("Progress: %.0f%%\n", projectProgress);
    tft.println("Sprint: " + sprintStatus);

    tft.setTextColor(TFT_YELLOW);
    tft.setCursor(10, 140);
    tft.println("Current Prompt:");
    tft.setTextColor(TFT_WHITE);
    tft.setTextSize(1);
    tft.println(currentPrompt);

    tft.setTextColor(TFT_GREEN);
    tft.setCursor(10, 200);
    tft.println("Tap to Approve");
}

void displayPage2() {  // Basic Info / Temp & Humidity
    tft.fillScreen(TFT_BLACK);
    tft.setTextColor(TFT_WHITE, TFT_BLACK);
    tft.setTextSize(2);
    tft.setCursor(20, 40);
    tft.println("System Status");
    tft.setCursor(20, 80);
    tft.println("Temp: 24.5 C");
    tft.println("Humidity: 42%");
    tft.println("IP: 192.168.1.XXX");
    tft.println("Uptime: 2h 14m");
}

void displayPage3() {  // RSS Feed Reader
    tft.fillScreen(TFT_BLACK);
    tft.setTextColor(TFT_MAGENTA, TFT_BLACK);
    tft.setTextSize(2);
    tft.setCursor(10, 20);
    tft.println("RSS Feeds");
    tft.setTextSize(1);
    tft.setCursor(10, 60);
    tft.println("1. AI News - New models dropping");
    tft.println("2. PCI SSF Updates");
    tft.println("3. DevOps Alerts");
    tft.println("\nTap to read full article");
}

void setup() {
    Serial.begin(115200);
    tft.init();
    tft.setRotation(1);
    tft.fillScreen(TFT_BLACK);

    if (!LittleFS.begin()) Serial.println("LittleFS failed");

    WiFiManager wm;
    if (!wm.autoConnect(deviceName.c_str())) {
        ESP.restart();
    }

    Serial.println("Connected! IP: " + WiFi.localIP().toString());

    // Simple API endpoint simulation (expand later with real /api/stats)
    server.on("/stats", HTTP_GET, [](AsyncWebServerRequest* request) {
        request->send(200, "application/json", "{\"agents\":3,\"subagents\":2,\"progress\":63.0}");
        });

    server.begin();

    displayPage1();  // Start on Agent Status page
}

void loop() {
    // Simple button simulation for page changing during testing
    // In real version use touch screen
    if (Serial.available()) {
        char c = Serial.read();
        if (c == 'n') {
            currentPage = (currentPage % 3) + 1;
            if (currentPage == 1) displayPage1();
            else if (currentPage == 2) displayPage2();
            else if (currentPage == 3) displayPage3();
            Serial.printf("Switched to Page %d\n", currentPage);
        }
    }

    delay(100);
}
