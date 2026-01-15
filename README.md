1. fontUtility.py will support ttf font to generate output format of *.c and *.h files
2. This is capable to generate 1, 2, 4, and 8 bits per pixel font bitmaps
3. *.h file contains the typedef structures for "font glyph and font"
4. User can provide input as font file, size, bpp, first character, last character, name of the font and output file name
5. Example command to run this utility: "py -3 fontGeneratorUtility_1.py --font Helvetica.ttf --size 17 --first 32 --last 127 --bpp 4 --name Helvetica17 --out Helvetica17"
6. This utility will support to store font in external flash memory
7. Find steps below to store font into external flash
8. Step-1: Generate the font files
   "python gen_font.py \
    --font Helvetica.ttf \
    --size 48 \
    --bpp 8 \
    --name font48 \
    --out font48"
  This produces: font48.c & font48.h
9. Step-2: Mark font data for QSPI flash

   Open font48.c and confirm this exists at the top:
     "#if defined(__GNUC__)
     #define FONT_SECTION __attribute__((section(".qspi_font"), used))
     #else
     #define FONT_SECTION
     #endif"
   
   Confirm ALL font data uses it:
     "static const uint8_t FONT_SECTION font48_Bitmap[];
     static const font_glyph_t FONT_SECTION font48_Glyphs[];
     const font_t FONT_SECTION font48;"
   
   This tells the linker not to place font data in internal flash or RAM.

10. Step-3: Configure QSPI in CubeMX
  In STM32CubeMX:
     QSPI
  
  Mode: Quad-SPI
     Flash size: 64 MB
     FIFO threshold: 4
     Clock prescaler: 2–4 (start safe)
     Sample shifting: Half cycle
  Enable:
     Memory-mapped mode
     Generate code.

 11. Step-4: Add QSPI region to linker script
     Open your linker script: STM32H753ZITx_FLASH.ld
     Add QSPI memory region
        MEMORY
        {
          FLASH    (rx)  : ORIGIN = 0x08000000, LENGTH = 2048K
          RAM_D1   (xrw) : ORIGIN = 0x24000000, LENGTH = 512K
          RAM_D2   (xrw) : ORIGIN = 0x30000000, LENGTH = 288K
          RAM_D3   (xrw) : ORIGIN = 0x38000000, LENGTH = 64K
          QSPI     (rx)  : ORIGIN = 0x90080000, LENGTH = 8M
        }

     Add QSPI font section
        .qspi_font :
        {
          . = ALIGN(4);
          KEEP(*(.qspi_font))
          . = ALIGN(4);
        } > QSPI

     This places font data at 0x90080000 inside external flash.
12. Step-5: Compile the font
      arm-none-eabi-gcc \
      -c font48.c \
      -mcpu=cortex-m7 \
      -mthumb \
      -O2 \
      -o font48.o

    Produces: font48.o

13. Step-6: Link font into firmware
    Add font48.o to your normal firmware build:
      arm-none-eabi-gcc \
      startup_stm32h753xx.s \
      main.c \
      font48.o \
      -TSTM32H753ZITx_FLASH.ld \
      -Wl,--gc-sections \
      -o firmware.elf

    Produces: firmware.elf

14. Step-7: Extract font data only
    Option A — Binary (fastest)
      arm-none-eabi-objcopy \
      -O binary \
      --only-section=.qspi_font \
      firmware.elf \
      font48_qspi.bin

    Option B — HEX (readable)
      arm-none-eabi-objcopy \
      -O ihex \
      --only-section=.qspi_font \
      firmware.elf \
      font48_qspi.hex

15. Step-8: Flash font to MT25QL512
    Using STM32CubeProgrammer (recommended)
      STM32_Programmer_CLI \
      -c port=SWD \
      -qspi \
      -w font48_qspi.bin 0x90080000
    This writes font data directly into QSPI flash.

16. Step-9: Enable QSPI memory-mapped mode (code)
    In main.c:
      MX_QUADSPI_Init();
      QSPI_EnableMemoryMappedMode();
    Example:
      HAL_QSPI_MemoryMapped(&hqspi, &sMemMappedCfg);

17. Step-10: Enable caches (CRITICAL on H7)
    SCB_EnableICache();
    SCB_EnableDCache();

    Without cache, QSPI reads are slow.

18. Step-11: Use the font at runtime
      #include "font48.h"

      extern const font_t font48;
      
      draw_text(&font48);

  ✔ Font is read directly from QSPI flash
  ✔ No RAM copy
  ✔ No memcpy
  ✔ No startup penalty

20. Step-12: 
  If font is updated at runtime:
      SCB_InvalidateDCache();

21. For multiple fonts run script to generate *.c and *.h for all the fonts.
    Example:
    python gen_font.py --font Roboto-Regular.ttf --size 32 --bpp 8 --name font32 --out font32
    python gen_font.py --font Roboto-Bold.ttf    --size 48 --bpp 8 --name font48 --out font48
    python gen_font.py --font Icons.ttf          --size 64 --bpp 2 --name icons64 --out icons64

22. Each generated .c must contain:
    #define FONT_SECTION __attribute__((section(".qspi_font"), used))

    And apply it to:
    static const uint8_t FONT_SECTION fontXX_Bitmap[];
    static const font_glyph_t FONT_SECTION fontXX_Glyphs[];
    const font_t FONT_SECTION fontXX;

23. Linker script update is same as above and the linker automatically packs fonts sequentially:
    0x90080000  font32
    0x90083A20  font48
    0x9008F910  icons64

24. Compile all fonts:
    arm-none-eabi-gcc -c font32.c  -mcpu=cortex-m7 -mthumb -O2 -o font32.o
    arm-none-eabi-gcc -c font48.c  -mcpu=cortex-m7 -mthumb -O2 -o font48.o
    arm-none-eabi-gcc -c icons64.c -mcpu=cortex-m7 -mthumb -O2 -o icons64.o

25. Link all fonts into firmware
    arm-none-eabi-gcc \
    startup_stm32h753xx.s \
    main.c \
    font32.o font48.o icons64.o \
    -TSTM32H753ZITx_FLASH.ld \
    -o firmware.elf

26. Flash ALL fonts at once
    arm-none-eabi-objcopy \
    -O binary \
    --only-section=.qspi_font \
    firmware.elf \
    fonts_qspi.bin

27. Flash to QSPI:
    STM32_Programmer_CLI \
    -c port=SWD \
    -qspi \
    -w fonts_qspi.bin 0x90080000

28. Use fonts in code
    #include "font32.h"
    #include "font48.h"
    #include "icons64.h"
    
    extern const font_t font32;
    extern const font_t font48;
    extern const font_t icons64;
    
    draw_text(&font32);
    draw_text(&font48);
    draw_icons(&icons64);

    ✔ Each font is accessed directly from QSPI
    ✔ No RAM usage
    ✔ No address math

  Verify layout (important)
    .qspi_font
    0x90080000 font32
    0x90083a20 font48
    0x9008f910 icons64













