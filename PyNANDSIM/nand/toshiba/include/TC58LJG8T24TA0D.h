#include <stdint.h>
#pragma pack(1)

typedef struct row_address_s
{
	 uint16_t  wl	    : 9;
	 uint16_t  plane	: 1;
	 uint16_t  block	: 10;
	 uint16_t   lun  	: 1;
}row_address_s_t;

typedef struct row_address_o
{
	 uint8_t addr1;
	 uint8_t addr2;
	 uint8_t addr3;
}row_address_o_t;

typedef union row_address
{
	row_address_o_t o;
	row_address_s_t s;
}row_address_t;

typedef struct column_address_o
{
	 uint8_t addr1;
	 uint8_t addr2;
}column_address_o_t;

typedef union column_address
{
	column_address_o_t o;
}column_address_t;

typedef struct address
{
	column_address_t column;
	row_address_t row;
}address_t;
