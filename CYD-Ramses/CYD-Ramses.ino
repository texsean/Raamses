#include <WiFi.h>
#include <WiFiManager.h>
#include <TFT_eSPI.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

TFT_eSPI tft = TFT_eSPI();

String serverIP = "192.168.7.251";   // Default - will be configurable
const int SERVER_PORT = 8080;

int rotation = 1;
String title = "AGENT MONITOR";

String overallStatus = "green";
String statusText = "All systems nominal";
int agents = 1;
int subagents = 0;
int tokensToday = 0;
String sprintStatus = "";

void colorTest() {
  Serial.println("=== COLOR TEST START ===");
  tft.fillScreen(TFT_RED);
  tft.setTextColor(TFT_WHITE, TFT_RED);
  tft.setTextSize(2);
  tft.setCursor(40, 100);
  tft.println("RED");
  delay(800);
  
  tft.fillScreen(TFT_GREEN);
  tft.setTextColor(TFT_BLACK, TFT_GREEN);
  tft.setCursor(40, 100);
  tft.println("GREEN");
  delay(800);
  
  tft.fillScreen(TFT_BLUE);
  tft.setTextColor(TFT_WHITE, TFT_BLUE);
  tft.setCursor(40, 100);
  tft.println("BLUE");
  delay(800);
  Serial.println("Color test complete");
}

void drawStatusBar() {
  uint16_t bgColor, textColor;
  
  if (overallStatus == "error" || overallStatus == "red") {
    bgColor = TFT_RED;
    textColor = TFT_WHITE;
  } else if (overallStatus == "orange") {
    bgColor = TFT_ORANGE;
    textColor = TFT_BLACK;
  } else if (overallStatus == "yellow") {
    bgColor = TFT_YELLOW;
    textColor = TFT_BLACK;
  } else {
    bgColor = TFT_DARKGREEN;
    textColor = TFT_WHITE;
  }
  
  tft.fillRect(0, 200, 240, 40, bgColor);
  tft.setTextColor(textColor, bgColor);
  tft.setTextSize(1);
  tft.setCursor(8, 212);
  tft.println(statusText.substring(0, 25));  // prevent overflow
}

void updateDisplay(String wifiStatus = "") {
  tft.setRotation(rotation);
  tft.fillScreen(TFT_BLACK);
  
  // Logo
  tft.fillRect(8, 8, 48, 48, TFT_GOLD);
  tft.setTextColor(TFT_BLACK, TFT_GOLD);
  tft.setTextSize(4);
  tft.setCursor(18, 12);
  tft.println("R");
  
  tft.setTextColor(TFT_CYAN, TFT_BLACK);
  tft.setTextSize(2);
  tft.setCursor(70, 20);
  tft.println(title);
  
  tft.drawLine(5, 68, 235, 68, TFT_ORANGE);
  
  // Data
  tft.setTextColor(TFT_LIGHTGREY, TFT_BLACK);
  tft.setTextSize(1);
  int y = 85;
  
  tft.setCursor(10, y); tft.print("Agents"); tft.setCursor(130, y); tft.println(String(agents)); y += 16;
  tft.setCursor(10, y); tft.print("Subagents"); tft.setCursor(130, y); tft.println(String(subagents)); y += 16;
  tft.setCursor(10, y); tft.print("Tokens"); tft.setCursor(130, y); tft.println(String(tokensToday)); y += 16;
  tft.setCursor(10, y); tft.print("Sprint"); tft.setCursor(130, y); tft.println(sprintStatus.substring(0,18)); y += 16;
  
  if (wifiStatus != "") {
    tft.setTextColor(TFT_ORANGE, TFT_BLACK);
    tft.setCursor(10, y); tft.println(wifiStatus);
  }
  
  drawStatusBar();
  
  tft.setTextColor(TFT_DARKGREY, TFT_BLACK);
  tft.setCursor(5, 225);
  tft.println("IP:" + WiFi.localIP().toString() + "  Touch=rotate");
}

void fetchStats() {
  Serial.println("\n--- Fetching from http://" + serverIP + ":" + String(SERVER_PORT) + "/stats ---");
  Serial.println("WiFi RSSI: " + String(WiFi.RSSI()) + "dBm | Local IP: " + WiFi.localIP().toString());
  
  HTTPClient http;
  String url = "http://" + serverIP + ":" + String(SERVER_PORT) + "/stats";
  http.setConnectTimeout(5000);
  http.setTimeout(8000);
  http.begin(url);
  
  int httpCode = http.GET();
  Serial.println("HTTP Code: " + String(httpCode));
  
  if (httpCode == HTTP_CODE_OK) {
    String payload = http.getString();
    Serial.println("Payload length: " + String(payload.length()));
    
    DynamicJsonDocument doc(4096);
    DeserializationError error = deserializeJson(doc, payload);
    
    if (!error) {
      overallStatus = doc["overall_status"] | "green";
      statusText = doc["last_alert"] | "All systems nominal";
      agents = doc["agents"] | 1;
      subagents = doc["subagents"] | 0;
      tokensToday = doc["tokens_today"] | 0;
      sprintStatus = doc["sprint_status"] | "Sprint 4/7";
      
      Serial.println("SUCCESS - Parsed data:");
      Serial.println("  Status: " + overallStatus);
      Serial.println("  Alert: " + statusText);
      Serial.println("  Agents: " + String(agents) + " | Subagents: " + String(subagents));
    } else {
      Serial.println("JSON ERROR: " + String(error.c_str()));
      overallStatus = "error";
      statusText = "JSON parse failed";
    }
  } else {
    overallStatus = "error";
    statusText = "Server unreachable (code " + String(httpCode) + ")";
    Serial.println("FAILED to reach server. Code -1 usually = DNS/WiFi/routing issue");
  }
  http.end();
}

void setup() {
  Serial.begin(115200);
  Serial.println("\n\n=== RAMSES CYD v3.2 - Network Diagnostics ===");
  
  tft.init();
  tft.setRotation(rotation);
  pinMode(21, OUTPUT);
  digitalWrite(21, HIGH);
  Serial.println("TFT + backlight initialized");
  
  colorTest();
  
  tft.fillScreen(TFT_BLACK);
  tft.setTextColor(TFT_GREEN, TFT_BLACK);
  tft.setTextSize(2);
  tft.setCursor(20, 80);
  tft.println("Ramses CYD");
  tft.setCursor(30, 120);
  tft.println("Connecting...");
  
  WiFiManager wm;
  wm.setClass("invert");
  wm.setConfigPortalTimeout(240);
  
  // Add parameter for server IP
  WiFiManagerParameter custom_server_ip("server_ip", "Server IP", serverIP.c_str(), 20);
  wm.addParameter(&custom_server_ip);
  
  Serial.println("Starting WiFiManager (SSID: Ramses-CYD)...");
  if (!wm.autoConnect("Ramses-CYD")) {
    Serial.println("WiFi failed - restarting");
    ESP.restart();
  }
  
  serverIP = custom_server_ip.getValue();  // Update from portal if changed
  if (serverIP.length() == 0) serverIP = "192.168.7.251";
  
  Serial.println("WiFi Connected!");
  Serial.println("Local IP: " + WiFi.localIP().toString());
  Serial.println("Server target: " + serverIP);
  Serial.println("RSSI: " + String(WiFi.RSSI()) + " dBm");
  
  fetchStats();
  updateDisplay();
  Serial.println("=== SETUP COMPLETE ===");
}

void loop() {
  static unsigned long lastFetch = 0;
  if (millis() - lastFetch > 8000) {
    fetchStats();
    updateDisplay();
    lastFetch = millis();
  }

  uint16_t x, y;
  if (tft.getTouch(&x, &y)) {
    Serial.println("Touch detected");
    rotation = (rotation + 1) % 4;
    updateDisplay();
    delay(250);
  }
  
  delay(50);
}
