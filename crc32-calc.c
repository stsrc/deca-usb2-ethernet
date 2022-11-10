#include <stdio.h>

int main(void)
{
  unsigned char data[] =
  {
    0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x0a, 0x0a,
    0x0a, 0x0a, 0x0a, 0x0a, 0x08, 0x06, 0x00, 0x01,
    0x08, 0x00, 0x06, 0x04, 0x00, 0x01, 0x0a, 0x0a,
    0x0a, 0x0a, 0x0a, 0x0a,  192,  168,    0,   66,
       0,    0,    0,    0,    0,    0,  192,  168,
       0,  135,    0,    0,    0,    0,    0,    0,
       0,    0,    0,    0,    0,    0,    0,    0,
       0,    0,    0,    0
  };
  unsigned int crc_table[] =
  {
    0x4DBDF21C, 0x500AE278, 0x76D3D2D4, 0x6B64C2B0,
    0x3B61B38C, 0x26D6A3E8, 0x000F9344, 0x1DB88320,
    0xA005713C, 0xBDB26158, 0x9B6B51F4, 0x86DC4190,
    0xD6D930AC, 0xCB6E20C8, 0xEDB71064, 0xF0000000
  };
  unsigned int n, crc=0;

  for (n=0; n<sizeof(data); n++)
  {
    crc = (crc >> 4) ^ crc_table[(crc ^ (data[n] >> 0)) & 0x0F];  /* lower nibble */
    crc = (crc >> 4) ^ crc_table[(crc ^ (data[n] >> 4)) & 0x0F];  /* upper nibble */
  }
  for (n=0; n<4; n++)  /* display the CRC, lower byte first */
  {
    printf("%02X ", crc & 0xFF);
    crc >>= 8;
  }
  printf("\n");
  return 0;
}
