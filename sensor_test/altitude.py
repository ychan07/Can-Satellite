import board
import busio
import adafruit_bmp280
import time

# I2C 통신 초기화
i2c = busio.I2C(board.SCL, board.SDA)

# BMP280 센서 초기화
# 여기서 address=0x76 부분을 추가합니다.
bmp280 = adafruit_bmp280.Adafruit_BMP280_I2C(i2c, address=0x76)

# 센서의 해수면 기압을 설정합니다.
bmp280.sea_level_pressure = 1013.25

print("BMP280 고도계 테스트 시작...")
print("----------------------------")

try:
    while True:
        temperature = bmp280.temperature
        pressure = bmp280.pressure
        altitude = bmp280.altitude

        print(f"온도: {temperature:.2f} °C")
        print(f"기압: {pressure:.2f} hPa")
        print(f"고도: {altitude:.2f} 미터")
        print("----------------------------")

        time.sleep(2) # 2초마다 값 업데이트
except KeyboardInterrupt:
    print("\n테스트 종료.")
