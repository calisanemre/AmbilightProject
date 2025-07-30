#include <FastLED.h>

#define LED_PIN 7
#define NUM_LEDS 100
#define BAUD_RATE 200000


CRGB leds[NUM_LEDS];
uint8_t brightness = 255;
bool setup_completed = false;

void starting_effect(CRGB *leds) {
  if (setup_completed) return;

  for (int i=0; i<NUM_LEDS; i++){
    leds[i] = CRGB::White;
    FastLED.show();
    delay(1);
    leds[i] = CRGB::Black;
  }

  for (int i=NUM_LEDS-2; i>0; i--){
    leds[i] = CRGB::White;
    FastLED.show();
    delay(1);
    leds[i] = CRGB::Black;
  }
  
  fill_solid(leds, NUM_LEDS, CRGB::White);
  FastLED.show();
  delay(100);
  fill_solid(leds, NUM_LEDS, CRGB::Black);
  FastLED.show();
}

void setup() {
  Serial.begin(BAUD_RATE);
  delay(1000);
  while(Serial.available()) {
    Serial.read();
  }
  FastLED.addLeds<WS2812B, LED_PIN, GRB>(leds, NUM_LEDS);
  FastLED.setBrightness(brightness);
  FastLED.setCorrection(TypicalPixelString);
  FastLED.clear();
  FastLED.show();

  starting_effect(leds);
  setup_completed = true;

  Serial.println("READY");
  Serial.flush();
}

void loop() {
  if (Serial.available()) {
    char command = Serial.read();
    
    if (command == 'd') {
      // Color data incoming
      int expected_bytes = NUM_LEDS * 3;
      int bytes_read = 0;
      unsigned long start_time = millis();
      
      while (bytes_read < expected_bytes && (millis() - start_time) < 1000) {
        if (Serial.available() >= 3) {
          int led_index = bytes_read / 3;
          
          if (led_index < NUM_LEDS) {
            leds[led_index].r = Serial.read();
            leds[led_index].g = Serial.read();
            leds[led_index].b = Serial.read();
            bytes_read += 3;
          } else {
            Serial.read();
            Serial.read();
            Serial.read();
            bytes_read += 3;
          }
        }
        delayMicroseconds(100);
      }
      
      if (bytes_read == expected_bytes) {
        FastLED.show();
      } else {
        Serial.print("ERROR: ");
        Serial.print(bytes_read);
        Serial.print("/");
        Serial.println(expected_bytes);
      }
      
    } else if (command == 't') {
      // Health check
      Serial.println("ALIVE");
    } else {
      // Clear any remaining unrecognized data
      while(Serial.available()) {
        Serial.read();
      }
    }
  }
  
  // Heartbeat message every 30 seconds
  static unsigned long last_heartbeat = 0;
  if (millis() - last_heartbeat > 30000) {
    Serial.println("WAITING");
    last_heartbeat = millis();
  }
}