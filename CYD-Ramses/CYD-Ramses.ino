#include <WiFi.h>
#include <WiFiManager.h>
#include <TFT_eSPI.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

TFT_eSPI tft = TFT_eSPI();

const char* SERVER_IP = "192.168.7.XXX";   // ← CHANGE TO YOUR LAPTOP IP

int currentPage = 0;  // 0 = Main, 1 = About, 2 = Detail, 3 = Full Response

String deviceName = "RAAMSES";
String agentStatus = "Agents: 4 | Sub: 9";
String projectStatus = "PCI-SSS-2.0 (67%)";
String tokenStatus = "Tokens: 18.4k / 25k (74%)";
String lastAlert = "Server 2 requesting permission";

String fullResponseText = "Full agent response would appear here with reply option.";

void drawMainPage() {
  tft.fillScreen(TFT_BLACK);
  
  // Logo (tap area)
  tft.fillRect(5, 8, 48, 48, TFT_GOLD);
  tft.setTextColor(TFT_BLACK, TFT_GOLD);
  tft.setTextSize(3);
  tft.setCursor(18, 18);
  tft.println("R");
  
  // Title
  tft.setTextColor(TFT_CYAN, TFT_BLACK);
  tft.setTextSize(2);
  tft.setCursor(68, 22);
  tft.println("AGENT VIEW");
  
  // Tan separator
  tft.drawLine(5, 68, 235, 68, TFT_ORANGE);
  
  // 2-Column Name | Value
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.setTextSize(2);
  int y = 85;
  tft.setCursor(10, y); tft.print("Server"); tft.setCursor(130, y); tft.println("EPS-01"); y += 22;
  tft.setCursor(10, y); tft.print("Project"); tft.setCursor(130, y); tft.println(projectStatus); y += 22;
  tft.setCursor(10, y); tft.print("Tokens"); tft.setCursor(130, y); tft.println(tokenStatus); y += 22;
  tft.setCursor(10, y); tft.print("Agents"); tft.setCursor(130, y); tft.println(agentStatus); y += 22;
  
  // Status Bar at bottom
  uint16_t barColor = TFT_GREEN;
  if (lastAlert.indexOf("permission") > -1) barColor = TFT_ORANGE;
  if (lastAlert.indexOf("error") > -1 || lastAlert.indexOf("critical") > -1) barColor = TFT_RED;
  
  tft.fillRect(0, 215, 240, 25, barColor);
  tft.setTextColor(TFT_BLACK, barColor);
  tft.setTextSize(1);
  tft.setCursor(10, 222);
  tft.println(lastAlert);
}

void drawAboutPage() {
  tft.fillScreen(TFT_BLACK);
  tft.setTextColor(TFT_GOLD, TFT_BLACK);
  tft.setTextSize(3);
  tft.setCursor(20, 30);
  tft.println("RAAMSES");
  tft.setTextSize(2);
  tft.setCursor(20, 80);
  tft.println("Remote AI Agent");
  tft.setCursor(20, 110);
  tft.println("Monitoring &");
  tft.setCursor(20, 140);
  tft.println("System Event");
  tft.setCursor(20, 170);
  tft.println("Supervisor");
  tft.setTextSize(1);
  tft.setCursor(20, 210);
  tft.setTextColor(TFT_LIGHTGREY, TFT_BLACK);
  tft.println("v1.0 - Tap to return");
}

void drawDetailPage() {
  tft.fillScreen(TFT_BLACK);
  tft.setTextColor(TFT_CYAN, TFT_BLACK);
  tft.setTextSize(2);
  tft.setCursor(10, 20);
  tft.println("Detail View");
  tft.setTextSize(1);
  tft.setCursor(10, 60);
  tft.println("Server EPS-01");
  tft.println("CPU 23%");
  tft.println("MEM 41%");
  tft.println("DISK 68%");
  tft.println("Uptime 14d 3h");
  tft.setCursor(10, 200);
  tft.setTextColor(TFT_LIGHTGREY, TFT_BLACK);
  tft.println("Tap to return");
}

void drawFullResponsePage() {
  tft.fillScreen(TFT_BLACK);
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.setTextSize(1);
  tft.setCursor(10, 10);
  tft.println(fullResponseText);
  tft.setCursor(10, 200);
  tft.setTextColor(TFT_GREEN, TFT_BLACK);
  tft.println("Reply | Back");
}

void handleTouch(int x, int y) {
  if (currentPage == 0) {
    if (x < 60 && y < 60) {  // Tap logo
      currentPage = 1; // About
    } else if (y > 80 && y < 200) { // Tap a data line
      currentPage = 2; // Detail
    } else if (y > 200) { // Tap status bar
      currentPage = 3; // Full response
    }
  } else {
    currentPage = 0; // Tap anywhere to go back to main
  }
  updateDisplay();
}

void updateDisplay() {
  if (currentPage == 0) drawMainPage();
  else if (currentPage == 1) drawAboutPage();
  else if (currentPage == 2) drawDetailPage();
  else if (currentPage == 3) drawFullResponsePage();
}

void setup() {
  Serial.begin(115200);
  tft.init();
  tft.setRotation(1);
  pinMode(21, OUTPUT);
  digitalWrite(21, HIGH);
  
  WiFiManager wm;
  wm.setClass("invert");
  if (!wm.autoConnect("Ramses-CYD")) ESP.restart();

  updateDisplay();
}

void loop() {
  uint16_t x, y;
  if (tft.getTouch(&x, &y)) {
    handleTouch(x, y);
    delay(300);
  }
  delay(50);
}
