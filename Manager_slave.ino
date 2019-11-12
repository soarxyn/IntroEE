// biblioteca do sonar
#include <HCSR04.h>

// bibliotecas do sensor RFID
#include <SPI.h>
#include <MFRC522.h>

const int BUZZER = 3;
const int RED = 2, GREEN = 4, BLUE = 7; // LED RGB
const int BOTAO = 8;
const int ECHO = 5, TRIGGER = 6;        // sonar
const int RST_PIN = 9, SS_PIN = 10;     // pinos de reset e SDA do sensor RFID

UltraSonicDistanceSensor sonar(TRIGGER, ECHO); // sonar
MFRC522 rfid(SS_PIN, RST_PIN);                 // sensor RFID

void setup() {
  Serial.begin(9600);

  SPI.begin();      //inicialização do barramento SPI do sensor RFID
  rfid.PCD_Init();  //inicialização do sensor RFID

  pinMode(BOTAO, INPUT);
  pinMode(BUZZER, OUTPUT);
  pinMode(RED, OUTPUT);
  pinMode(GREEN, OUTPUT);
  pinMode(BLUE, OUTPUT);
  digitalWrite(RED, HIGH);
}

bool contandoTempo = false;
unsigned long long int numeroDeMedicoes;
double presenca;
String request;

void loop() {
  if(rfid.PICC_IsNewCardPresent() && rfid.PICC_ReadCardSerial()) { // se o cartão lido é diferente do anterior
    if(!contandoTempo) {
      tone(BUZZER, 880);
      delay(300);
      noTone(BUZZER);
      Serial.println("start"); // imprime no serial para começar a contagem
      contandoTempo = true;
      numeroDeMedicoes = 0;
      presenca = 1;
      digitalWrite(RED, LOW);
      digitalWrite(GREEN, HIGH);
    } else {
      tone(BUZZER, 830);
      delay(600);
      noTone(BUZZER);
      Serial.println("stop"); // imprime no serial para encerrar a contagem
      contandoTempo = false;
      digitalWrite(GREEN, LOW);
      digitalWrite(RED, HIGH);
    }
    rfid.PICC_HaltA();      // parada da leitura
    rfid.PCD_StopCrypto1(); // parada da criptografia no PCD
  }
  if(digitalRead(BOTAO) == HIGH) {
      Serial.println("emergency"); // imprime no serial para avisar uma emergência
      if(contandoTempo) {
        tone(BUZZER, 830);
        delay(600);
        noTone(BUZZER);
        contandoTempo = false;
        digitalWrite(GREEN, LOW);
        digitalWrite(RED, HIGH);
      }
      while(digitalRead(BOTAO) == HIGH) {}
  }
  if(contandoTempo) {
    if(sonar.measureDistanceCm() > 120.0)
      presenca = double(presenca*numeroDeMedicoes - 1)/double(++numeroDeMedicoes);
    else
      presenca = double(presenca*numeroDeMedicoes + 1)/double(++numeroDeMedicoes);

  }
  // apenas responde quando dados são recebidos:
  if(Serial.available() > 0) {
    request = Serial.readString();
    if(request == "#r\n\0")
      Serial.println(presenca);
    else if(request == "stop\n\0" && contandoTempo) {
      tone(BUZZER, 830);
      delay(600);
      noTone(BUZZER);
      contandoTempo = false;
      digitalWrite(GREEN, LOW);
      digitalWrite(RED, HIGH);
    }
  }
}
