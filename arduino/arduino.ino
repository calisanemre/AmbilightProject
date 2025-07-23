#include <Arduino.h>
#include <FastLED.h>

#define LED_PIN     6
#define NUM_LEDS    32
#define BAUD_RATE   115200
#define MAX_DECIMAL 4

CRGB leds[NUM_LEDS];
uint8_t data[NUM_LEDS * 3];

void setup() {
  Serial.begin(BAUD_RATE);
  FastLED.addLeds<WS2812, LED_PIN, GRB>(leds, NUM_LEDS);
  FastLED.clear();
  FastLED.show();
  Serial.setTimeout(50);
}

void loop() {
  // === Brightness Control ===
  if (Serial.peek() == 'b' && Serial.available() >= MAX_DECIMAL + 1) { // Brightness protocol
    Serial.read(); 
    char buffer[MAX_DECIMAL+1];
    Serial.readBytes(buffer, MAX_DECIMAL);
    buffer[MAX_DECIMAL] = '\0';

    int level = atoi(buffer);
    level = constrain(level, 0, 255);
    FastLED.setBrightness(level);
    FastLED.show();
  }

  // === LED Color Data ===  
  if (Serial.available() >= NUM_LEDS * 3) {
    Serial.readBytes(data, NUM_LEDS * 3);
    for (int i = 0; i < NUM_LEDS; i++) {
      leds[i] = CRGB(data[i * 3], data[i * 3 + 1], data[i * 3 + 2]);
    }
    FastLED.show();
  }
}
