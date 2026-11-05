# Официальный валидатор

`wff-validator.jar` собран без изменений из репозитория Google:
https://github.com/google/watchface/tree/d1cdafa953c95d5554fc54df4bc3948befbefc4d/third_party/wff

Коммит: `d1cdafa953c95d5554fc54df4bc3948befbefc4d`.

Инструмент поддерживает версии до 5; проект всегда передаёт аргумент **4**, поэтому
проверяется схема v4. Валидатор содержит официальные XSD. Лицензия исходников —
Apache 2.0 (`WFF-LICENSE.txt`). Зависимости валидатора перечислены в исходном
`specification/validator/build.gradle`; их notices находятся в JAR.

Повторная сборка (JDK 17+, Gradle 8.13):

```sh
git clone https://github.com/google/watchface.git
cd watchface
git checkout d1cdafa953c95d5554fc54df4bc3948befbefc4d
cd third_party/wff
./gradlew :specification:validator:executable-jar
```

Результат: `specification/validator/build/libs/wff-validator.jar`.
Этот JAR работает только при разработке/сборке и не попадает в APK.

SHA-256 включённого JAR:
`37b8ecd618ebf47ef9c1543251a5a6af511796810e77f890a52b3733f991cda8`.

Проверка вручную из корня TwentyFour:

```sh
java -jar tools/wff-validator.jar 4 --stop-on-fail watchface/src/main/res/raw/watchface.xml
```

Флаг `--stop-on-fail` обязателен для корректного ненулевого exit code при ошибке.
Gradle дополнительно проверяет наличие `PASSED` в отчёте.
