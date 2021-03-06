from PIL import Image
### Image Processing Functions

"""
# Define Constants - RC1
HEADOFFSET = 726 # Distance between the same line of primitives on two different heads (in pixels)
PRIMITIVEOFFSET = 12 # Distance between two different primitives on the same head (in pixels)
VOFFSET = -2 # Vertical distance between the two printheads
"""

class ImageProcessor:
    # Distance between the same line of primitives on two different heads (in pixels)
    # Distance between the two cartridges in pixels
    HEADOFFSET = 726

    # Distance between two different primitives on the same head (in pixels)
    # Distance between the two rows of nozzles
    PRIMITIVEOFFSET = 12

    # Vertical distance between the two printheads
    VOFFSET = 0

    # Steps per nozzle (actually per half nozzle as we are doing 600 dpi)
    SPN = 3.386666

    # Movement offset in pixels. This is how far down we move between lines.
    # Can be changed to any odd number less than 103. A larger number means the
    # print will be faster but put down less ink and have less overlap
    mOffset = 103

    # Firings per step variable. Currently cannot set different firings per step for
    # different print heads but this will be implemented very soon - won't take me
    # long to implement.
    fps = 1

    outputFile = None

    def __init__(self, horizontal_offset=None, vertical_offset=None, overlap=None):
        if horizontal_offset:
            self.HEADOFFSET = horizontal_offset

        if vertical_offset:
            self.VOFFSET = vertical_offset

        if overlap:
            self.mOffset = overlap

        print('Image processor with {} {} {}'.format(self.HEADOFFSET, self.VOFFSET, self.mOffset))

    def sliceImage(self, inputFileName, outputFileName):
        #directory = direct
        # Global variables to hold the images we are working with
        global outputImages
        global pixelMatrices

        outputImages = []
        pixelMatrices = []

        outputFile = open(outputFileName, 'wb')

        # Go to our working directory and open/create the output file
        #os.chdir(directory)
        #hexOutput = outputFile
        self.outputFile = outputFile

        # Open our image and split it into its odd rows and even rows
        inputImage = Image.open(inputFileName)

        inputs = self.splitImageTwos(inputImage)

        # Get the size of the input images and adjust width to be that of the output
        width, height = inputs[0].size
        width += self.HEADOFFSET + self.PRIMITIVEOFFSET

        # Adjust the height. First make sure it is a multiple of mOffset.
        height += (self.mOffset - height % self.mOffset)

        # Then add an extra 2 rows of blank lines.
        height += (104 * 2)

        # Create the output images and put them into a list for easy referencing
        outputImages = [
                Image.new('RGBA', (width , height), (255, 255, 255, 255))
                for i in range(4)
        ]

        # Paste the split input image into correct locations on output images

        # (0, VOFFSET + 104) = (0, 104)
        # (PRIMITIVEOFFSET, VOFFSET + 104) = (12, 104)

        pasteLocations = (
            (
                self.HEADOFFSET,
                (int(208 / self.mOffset) * self.mOffset) / 2
            ),
            (
                self.HEADOFFSET + self.PRIMITIVEOFFSET,
                (int(208 / self.mOffset) * self.mOffset) / 2
            ),
            (
                0,
                (int(208 / self.mOffset) * self.mOffset) / 2 + self.VOFFSET
            ),
            (
                self.PRIMITIVEOFFSET,
                (int(208 / self.mOffset) * self.mOffset) / 2 + self.VOFFSET
            )
        )


        for i in range(4):
            outputImages[i].paste(inputs[i % 2], pasteLocations[i])

        pixelMatrices = [
            outputImages[i].load()
            for i in range(4)
        ]

        # We have our input images and their matrices. Now we need to generate
        # the correct output data.
        self.writeCommands()

    def writeCommands(self):
        width, height = outputImages[0].size

        # Ignore empty pixels added to the bottom of the file.
        height -= (int(208/self.mOffset) * self.mOffset)

        yposition = 0

        for y in xrange(height/self.mOffset*2 + 1):
            # Print out progress
            print '{} out of {}.'.format(y + 1, height/self.mOffset*2 + 1)

            move = 0
            xposition = 0

            # Iterate through the width of the image(s)
            for x in xrange(width):

                firings = [
                        [
                            self.calculateFiring(x, y, a, 0),
                            self.calculateFiring(x, y, a, 1)
                        ]
                    for a in xrange(13)
                ]

                if not any([any(firings[i]) for i in xrange(len(firings))]):
                    #move += (int((x + 1) * SPN) - xposition - move)
                    move = (int((x + 1) * self.SPN) - xposition)
                    continue
                elif move != 0 :
                    xposition += move
                    #outputStream.write('M X %d\n' % move)
                    self.writeMovementCommand('X', move)
                    move = (int((x + 1) * self.SPN) - xposition)

                for f in xrange(self.fps):
                    # Iterate through addresses
                    for a in xrange(13):
                        if firings[a] == [0]:
                            continue

                        #for i in xrange(2):
                        self.writeFiringCommand(a, firings[a][0], firings[a][1])

            # Move back
            if xposition != 0:
                #outputStream.write('M X 0\n')
                self.writeMovementCommand('X', 0)
                xposition = 0

            # Move down
            movey = int(self.mOffset * (y + 1) * self.SPN) - yposition
            #outputStream.write('M Y %d\n' % -movey)
            self.writeMovementCommand('Y', -movey)
            yposition += movey


        # Reset X and Y positions
        #outputStream.write('M Y 0\n')
        #outputStream.write('M X 0\n')
        self.writeMovementCommand('X', 0)
        self.writeMovementCommand('Y', 0)

        self.outputFile.close()

    def calculateFiring(self, xPos, yPos, addr, side):
        # Lookup tables to convert address to position
        positions = (
            (0, 10, 7, 4, 1, 11, 8, 5, 2, 12, 9, 6, 3),
            (9, 6, 3, 0, 10, 7, 4, 1, 11, 8, 5, 2, 12)
        )

        # 13 nozzles in a primitive, these are the number of the nozzles, in the
        # correct firing order. The second grouping is for the even side? it is
        # simply offset by the first 3 nozzles, which is strange. I would have
        # assumed it to be just; the reverse of the first one, to maintain
        # maximum physical distance between firing nozzles.

        # The second one IS for the even side, and by shifting the order 3
        # settings, you can use the same index to get the correct firing for
        # each primitive.

        firing = 0

        x = xPos

        # Calculate the y offset for the given address

        # odd side?
        y = (yPos * self.mOffset)/2 + (positions[0][addr] * 2)

        # ensure that yPos is even
        if yPos % 2:
            y += 1

        for i in range(4):
            # if this pixel is on, set the corresponding bit in firing
            if pixelMatrices[side*2][x, y][2] <= 200:
                firing += 1 << (i*2)
            y += 26


        y = (yPos * self.mOffset)/2 + (positions[1][addr] * 2)

        # ensure that yPos is even
        if yPos % 2:
            y += 1

        for i in range(4):
            # if this pixel is on, set the corresponding bit in firing
            if pixelMatrices[side*2 + 1][x, y][2] <= 200:
                firing += 1 << (i*2 + 1)
            y += 26

        return firing

    '''
    Splits an input image into two images.
    '''
    def splitImageTwos(self, image):
        width, height = image.size

        # If the height of the input image isn't a multiple of 4, round it up.
        if height % 4 != 0:
            # (height % 4) will be the remainder left over
            # so 4 - remainder will be the difference required
            height += (4 - (height % 4))

        # New images to store the split rows. Each image has half the height,
        # since we're splitting the image vertically.
        odd = Image.new('RGBA', (width, height/2), (255, 255, 255, 255))
        even = Image.new('RGBA', (width, height/2), (255, 255, 255, 255))

        # References to the pixel data.
        evenMatrix = even.load()
        oddMatrix = odd.load()
        inputMatrix = image.load()

        # Divide by 4 because we're copying two rows at a time (why?)
        # Subtract 1 because of zero-offset.
        for y in xrange((height / 4) - 1):
            for x in xrange(width):
                oddMatrix[x, y*2] = inputMatrix[x, y*4]
                oddMatrix[x, y*2+1] = inputMatrix[x, y*4+1]

                evenMatrix[x, y*2] = inputMatrix[x, y*4+2]
                evenMatrix[x, y*2+1] = inputMatrix[x, y*4+3]

        # Handle the final row(s) specially
        # This shouldn't be necessary, since we know how many extras
        # (non-existant) we added.
        y = (height / 4) - 1
        for x in xrange(width):
            if y*4 < image.size[1]: oddMatrix[x, y*2] = inputMatrix[x, y*4]
            if y*4 + 1 < image.size[1]: oddMatrix[x, y*2+1] = inputMatrix[x, y*4+1]

            if y*4 + 2 < image.size[1]: evenMatrix[x, y*2] = inputMatrix[x, y*4+2]
            if y*4 + 3 < image.size[1]: evenMatrix[x, y*2+1] = inputMatrix[x, y*4+3]

        return (odd, even)

    def writeMovementCommand(self, axis, steps):
        self.outputFile.write('M {} {}\n'.format(axis, steps))

    def writeFiringCommand(self, a, firing1, firing2):
        # The multiplexer doesn't use the first output, for startup reasons.
        a = a + 1

        address =  (a & 0b00000001) << 3
        address += (a & 0b00000010) << 1
        address += (a & 0b00000100) >> 1
        address += (a & 0b00001000) >> 3

        #self.outputFile.write('F {} {} {}\n'.format(a, firing1, firing2))

        outputStream = self.outputFile

        outputStream.write(chr(1)) # Fire command
        outputStream.write(chr(firing1)) # Relevant firing data, i.e. which primitive(s) to fire
        outputStream.write(chr(address)) # The address we're firing within the primitive(s)
        outputStream.write('\n')
        outputStream.write(chr(1)) # Fire command
        outputStream.write(chr(firing2)) # Relevant firing data, i.e. which primitive(s) to fire
        outputStream.write(chr(address)) # The address we're firing within the primitive(s)
        outputStream.write('\n')
