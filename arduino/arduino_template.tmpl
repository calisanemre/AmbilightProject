#include <FastLED.h>
#include <EEPROM.h>

struct Config {
  uint8_t led_pin;
  uint8_t led_count;
  uint32_t baud_rate;
  uint8_t update_rate;
  uint8_t version = 1;
};

Config config;
CRGB* leds = nullptr;
uint8_t brightness = 255;
bool setup_completed = false;


void loadConfigFromEEPROM(Config& config) {
  EEPROM.get(0, config);
  if (config.version != 1) {
    config.led_pin = 7;
    config.led_count = 100;
    config.baud_rate = 250000;
    config.update_rate = 30;
    config.version = 1;

    EEPROM.put(0, config);
  }
}

void parseConfigFromBytes(const uint8_t* data, size_t dataLength, Config &out) {
  if (dataLength != sizeof(Config)) {
    Serial.println("ERROR: Invalid config size!");
    return;
  }
  memcpy(&out, data, sizeof(Config));
}


void starting_effect(CRGB* leds, int count) {
  if (setup_completed) return;
  for (int i = 0; i < count; i++) {
    leds[i] = CRGB::White;
    FastLED.show();
    delay(1);
    leds[i] = CRGB::Black;
  }

  for (int i = count - 2; i > 0; i--) {
    leds[i] = CRGB::White;
    FastLED.show();
    delay(1);
    leds[i] = CRGB::Black;
  }
  fill_solid(leds, count, CRGB::White);
  FastLED.show();
  delay(100);
  fill_solid(leds, count, CRGB::Black);
  FastLED.show();
}


void applyConfig(const Config& cfg) {
  if (leds != nullptr) {
    delete[] leds;
  }

  leds = new CRGB[cfg.led_count];

  switch (cfg.led_pin) {
      case 5: FastLED.addLeds<WS2812B, 5, GRB>(leds, cfg.led_count); break;
      case 6: FastLED.addLeds<WS2812B, 6, GRB>(leds, cfg.led_count); break;
      case 7: FastLED.addLeds<WS2812B, 7, GRB>(leds, cfg.led_count); break;
      default: FastLED.addLeds<WS2812B, 7, GRB>(leds, cfg.led_count); break;
    }
  Serial.begin(cfg.baud_rate);
  delay(1000);
  while (Serial.available()) Serial.read();
  FastLED.setBrightness(brightness);
  FastLED.setCorrection(TypicalPixelString);
  FastLED.clear();
  FastLED.show();

  starting_effect(leds, cfg.led_count);
  setup_completed = true;
  Serial.println("READY");
  Serial.flush();
}


void setup() {
  loadConfigFromEEPROM(config);
  applyConfig(config);
}


void loop() {
  if (Serial.available()) {
    char command = Serial.read();

    if (command == 'd') {
      int expected_bytes = config.led_count * 3;
      int bytes_read = 0;
      unsigned long start_time = millis();

      while (bytes_read < expected_bytes && (millis() - start_time) < 1000) {
        if (Serial.available() > 0) {
          bytes_read += Serial.readBytes((char*)(leds), expected_bytes - bytes_read);
        }
      }

      if (bytes_read == expected_bytes) {
        FastLED.show();
        Serial.println("OK");
      } else {
        Serial.print("ERROR: ");
        Serial.print(bytes_read);
        Serial.print("/");
        Serial.println(expected_bytes);
        while(Serial.available()) Serial.read();
      }

    } else if (command == 'w') {
      unsigned long startTime = millis();
      while (Serial.available() < sizeof(Config)) {
        if (millis() - startTime > 1000) { 
          Serial.println("ERROR: Config data timeout!");
          while(Serial.available()) Serial.read();
          return; 
        }
        delay(1);
      }
      uint8_t buffer[sizeof(Config)];
      Serial.readBytes(buffer, sizeof(Config));
      Config new_cfg;
      parseConfigFromBytes(buffer, sizeof(Config), new_cfg);
      EEPROM.put(0, new_cfg);
      config = new_cfg;

      Serial.println("CONFIG_SAVED");
      delay(100);
    }

    else if (command == 't') {
      Serial.println("ALIVE");
    } else {
      while (Serial.available()) Serial.read(); 
    }
  }

  static unsigned long last_heartbeat = 0;
  if (millis() - last_heartbeat > 30000) {
    Serial.println("WAITING");
    last_heartbeat = millis();
  }
}