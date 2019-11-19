#include <LiquidCrystal.h>

// display
const int rs = 12, en = 11, d4 = 5, d5 = 4, d6 = 3, d7 = 2;
LiquidCrystal lcd(rs, en, d4, d5, d6, d7);

const int BUZZER = 9;
const int LED = 6;
const int TEMPO_DE_BUZINA = 10000;    // em milissegundos

void setup() {
  Serial.begin(4800);
  lcd.begin(16, 2);
  pinMode(BUZZER, OUTPUT);
  pinMode(LED, OUTPUT);
}

bool emergencia = false;
int estacao;
String request;

void loop() {
  if(!emergencia) {
    lcd.setCursor(0, 0);
    lcd.print("Operacao normal");
  } else {
    lcd.clear();
    digitalWrite(LED, HIGH);
    lcd.setCursor(0, 0);
    lcd.print("Emergencia na es");
    lcd.setCursor(0, 1);
    lcd.print("tacao 0");
    int tInicial = millis();
    int tFinal = millis();
    int deltaT = tFinal - tInicial;
    while(deltaT < TEMPO_DE_BUZINA) {
      for(int x = 0; x < 180; x++) {
        //converte graus para radiando e depois obtém o valor do seno
        double seno = sin(x*3.1416/180);
        //gera uma frequência a partir do valor do seno
        int frequencia = 2000 + int(seno*1000);
        tone(BUZZER, frequencia);
        delay(2);
        tFinal = millis();
        deltaT = tFinal - tInicial;
      }
    }
    noTone(BUZZER);
    digitalWrite(LED, LOW);
    emergencia = false;
    lcd.clear();
  }
  if(Serial.available() > 0) {
    request = Serial.readString();
    if(request == "emergency\n\0")
      emergencia = true;

  }
}
