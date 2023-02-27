#!/bin/python
from sys import argv
from subprocess import check_output

chars = [' ', '░', '▒', '▓', '█', '█']
ascii_chars = [' ', '+', 'O', '$', '#', '#']
sq_chars = ['▘', '']
sm_chars = [' ', '▗', '▖', '▄', '▝', '▐', '▞', '▟', '▘', '▚', '▌', '▙', '▀', '▜', '▛', '█']
sm_ascii_chars = [' ', ',', ',', 'm', '`', ')', '/', 'd', '`','\\', '(', "b", '^', 'q', 'p', '#']


def colored_text(text, color):
    return f"\x1b[38;2;{color[0]};{color[1]};{color[2]}m{text}"


def colored_fb_text(text, foreground, background):
    return f"\x1b[38;2;{foreground[0]};{foreground[1]};{foreground[2]}m" + \
           f"\x1b[48;2;{background[0]};{background[1]};{background[2]}m{text}"


def average_pixels(pixels):
    avg = [0, 0, 0]

    if len(pixels) == 0:
        return avg

    for pixel in pixels:
        avg[0] += pixel[0]
        avg[1] += pixel[1]
        avg[2] += pixel[2]

    avg[0] = int(avg[0] / len(pixels))
    avg[1] = int(avg[1] / len(pixels))
    avg[2] = int(avg[2] / len(pixels))

    return avg


def main():
    # Arguments
    file_name = argv[1]
    mode = 0

    if len(argv) > 2:
        match argv[2]:
            case 'rgb-full': mode = 0
            case 'rgb-half': mode = 1
            case 'rgb-small': mode = 2
            case 'mono-full': mode = 3
            case 'mono-half': mode = 4
            case 'mono-small': mode = 5
            case 'ascii-full': mode = 6
            case 'ascii-half': mode = 7
            case 'ascii-small': mode = 8
            case 'mono-braille': mode = 9
            case 'rgb-braille': mode = 10

    # Extract width from ffprobe
    width = check_output(["sh", "-c", f"ffprobe -i \"{file_name}\" -v quiet -show_entries stream=width -hide_banner"]).decode('utf8')
    width = int(width.split('\n')[1].split('=', 1)[1])

    # Get data
    content = check_output(["sh", "-c", f"ffmpeg -i \"{file_name}\" -f rawvideo -filter:v \"format=rgb24\" pipe:1 2>/dev/null"])
    data = []

    typ = ""
    for i in range(0, len(content), 3):
        rgb = [content[i], content[i+1], content[i+2]]
        data.append(rgb)

    mode_type = mode % 3
    if mode >= 9:
        mode_type = 4

    if mode_type == 1:
        for i in range(int((len(data) / width % 2) * width)):
            data.append([0, 0, 0])
    elif mode_type == 2 or mode_type == 4:
        for i in range(int((len(data) / width % 4) * width)):
            data.append([0, 0, 0])

    for i in range(len(data)):
        x = i % width
        y = int(i / width)

        # in half mode, skip every second line
        if mode_type == 1 and y % 2 == 1:
            continue

        # When small or braille, skip 3/4 rows and every second line
        if (mode_type == 2 or mode_type == 4) and (y % 4 != 0 or x % 2 == 1):
            continue

        # shared code for full
        if mode_type == 0:
            rgb = data[i]
            avr = (rgb[0] + rgb[1] + rgb[2]) / 3

        # shared code for half
        elif mode_type == 1:
            rgb = average_pixels([data[i], data[i+width]])
            avr = (rgb[0] + rgb[1] + rgb[2]) / 3

        # shared code for small
        elif mode_type == 2:
            # Get the 4 pixels, and convert into a binary number like 0110
            # This is ordered top left, top right, bottom left, bottom right
            # Then the correct character is chosen from the array
            datas = [
                average_pixels([data[i], data[i+width]]),
                average_pixels([data[i+1], data[i+1+width]]),
                average_pixels([data[i + width*2], data[i + width*3]]),
                average_pixels([data[i+1 + width*2], data[i+1 + width*3]])
            ]

            pixels = []
            index = 0

            for i in range(4):
                rgb = datas[i]
                avr = (rgb[0] + rgb[1] + rgb[2]) / 3
                black = 1 if avr/0xff > 0.5 else 0

                pixels.append(black)
                index += black << 3-i

        # shared code for braille
        elif mode_type == 4:
            # Get the 8 pixels, and convert into a binary number like 01100010
            # This is ordered tl, mtl, mbl, tr, mtr, mbr, bl, br
            # tl = top left (⠁), mbl = middle bottom left (⠄)
            # Then the correct character is chosen from the array
            datas = [
                data[i], data[i+width],
                data[i+width*2], data[i+1],
                data[i+1 + width], data[i+1 + width*2],
                data[i+width*3], data[i+1 + width*3]
            ]

            pixels = []
            index = 0

            for i in range(8):
                rgb = datas[i]
                avr = (rgb[0] + rgb[1] + rgb[2]) / 3
                black = 1 if avr/0xff > 0.5 else 0

                pixels.append(black)
                index += black << i

        # mode specific code
        match mode:
            # rgb-full
            case 0:
                typ += colored_text("██", rgb)

            # monochrome-full
            case 3:
                typ += chars[int(avr/0xff*5)] * 2

            # ascii-full
            case 6:
                typ += ascii_chars[int(avr/0xff*5)] * 2

            # rgb-half
            case 1:
                typ += colored_text("█", rgb)

            # monochrome-half
            case 4:
                typ += chars[int(avr/0xff*5)]

            # ascii-half
            case 7:
                typ += ascii_chars[int(avr/0xff*5)]

            # monochrome-small
            case 5:
                typ += sm_chars[index]

            # rgb-small
            case 2:
                foreground_pixels = []
                background_pixels = []

                for i in range(4):
                    if pixels[i] == 1:
                        foreground_pixels.append(datas[i])
                    else:
                        background_pixels.append(datas[i])

                foreground = average_pixels(foreground_pixels)
                background = average_pixels(background_pixels)
                typ += colored_fb_text(sm_chars[index], foreground, background)

            # ascii-small
            case 8:
                typ += sm_ascii_chars[index]

            # braille
            case 9:
                typ += chr(0x2800 + index)

            # braille-rgb
            case 10:
                foreground_pixels = []
                background_pixels = []
                war = 0

                for i in range(8):
                    if pixels[i] == 1:
                        foreground_pixels.append(datas[i])
                        war += 1
                    else:
                        background_pixels.append(datas[i])
                        war -= 1

                foreground = average_pixels(foreground_pixels)
                background = average_pixels(background_pixels)

                if len(background_pixels) == 0:
                    typ += colored_fb_text(' ', foreground, foreground)
                elif len(foreground_pixels) == 0:
                    typ += colored_fb_text(' ', background, background)
                elif war < 0:
                    typ += colored_fb_text(chr(0x2800 + index), foreground, background)
                else:
                    typ += colored_fb_text(chr(0x2800 + (0xff - index)), background, foreground)

        if x == width - 1 - (1 if mode_type == 2 else 0) - (1 if mode_type == 4 else 0):
            print(typ)
            typ = ""


if __name__ == "__main__":
    main()

