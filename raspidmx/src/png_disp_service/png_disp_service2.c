//-------------------------------------------------------------------------
//
// The MIT License (MIT)
//
// Copyright (c) 2013 Andrew Duncan
//
// Permission is hereby granted, free of charge, to any person obtaining a
// copy of this software and associated documentation files (the
// "Software"), to deal in the Software without restriction, including
// without limitation the rights to use, copy, modify, merge, publish,
// distribute, sublicense, and/or sell copies of the Software, and to
// permit persons to whom the Software is furnished to do so, subject to
// the following conditions:
//
// The above copyright notice and this permission notice shall be included
// in all copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
// OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
// MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
// IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
// CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
// TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
// SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
//
//-------------------------------------------------------------------------

#define _GNU_SOURCE

#include <assert.h>
#include <ctype.h>
#include <signal.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

#include "backgroundLayer.h"
#include "imageLayer.h"
#include "key.h"
#include "loadpng.h"

#include "bcm_host.h"

#include <stdio.h>
#include <string.h>

/*This is the sample program to notify us for the file creation and file deletion takes place in “/tmp” directory*/
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <sys/types.h>
#include <linux/inotify.h>

//-------------------------------------------------------------------------

#define NDEBUG

//-------------------------------------------------------------------------

const char *program = NULL;

//-------------------------------------------------------------------------

volatile bool run = true;

//-------------------------------------------------------------------------

static void
signalHandler(
    int signalNumber)
{
    switch (signalNumber)
    {
    case SIGINT:
        run = false;
        break;

    case SIGTERM:
        run = false;
        break;
    };

    printf ("\nTerminate PNG display service\n");

}



#define EVENT_SIZE  ( sizeof (struct inotify_event) )
#define EVENT_BUF_LEN     ( 1024 * ( EVENT_SIZE + 16 ) )

//-------------------------------------------------------------------------


//-------------------------------------------------------------------------

int main(int argc, char *argv[])
{
    uint16_t background = 0x0;
    int32_t layer = 2;
    uint32_t displayNumber = 0;

    program = basename(argv[0]);

    //---------------------------------------------------------------------


    //---------------------------------------------------------------------

    if (signal(SIGINT, signalHandler) == SIG_ERR)
    {
        perror("installing SIGINT signal handler");
        exit(EXIT_FAILURE);
    }

    //---------------------------------------------------------------------

    if (signal(SIGTERM, signalHandler) == SIG_ERR)
    {
        perror("installing SIGTERM signal handler");
        exit(EXIT_FAILURE);
    }


    //---------------------------------------------------------------------

    bcm_host_init();

    //---------------------------------------------------------------------

    DISPMANX_DISPLAY_HANDLE_T display
        = vc_dispmanx_display_open(displayNumber);
    assert(display != 0);

    //---------------------------------------------------------------------

    DISPMANX_MODEINFO_T info;
    int result = vc_dispmanx_display_get_info(display, &info);
    assert(result == 0);

    //---------------------------------------------------------------------

    BACKGROUND_LAYER_T backgroundLayer;

    if (background > 0)
    {
        initBackgroundLayer(&backgroundLayer, background, 0);
    }

    char  filename[1024];
    strcpy(filename, "/home/pi/Desktop/App/rgba.png");

    IMAGE_LAYER_T imageLayer;


    //---------------------------------------------------------------------
    while(true)
    {
        usleep(1000000);
        if (loadPng(&(imageLayer.image), filename) == false)
        {
            fprintf(stderr, "unable to load %s\n", filename);
        }
        else
            break;
    }

    createResourceImageLayer(&imageLayer, layer);

    //---------------------------------------------------------------------

    DISPMANX_UPDATE_HANDLE_T update = vc_dispmanx_update_start(0);
    assert(update != 0);

    if (background > 0)
    {
        addElementBackgroundLayer(&backgroundLayer, display, update);
    }

    addElementImageLayerCentered(&imageLayer,
                                 &info,
                               display,
                               update);

    result = vc_dispmanx_update_submit_sync(update);

    assert(result == 0);

    //---------------------------------------------------------------------
    int cnt = 0;

    while (run)
    {
        printf( "\nEnter png filename:");
        scanf("%s", filename);
        int r = strcmp(filename, "close");
        if (r == 0)
        {
            printf("\nFinish\n");
            run = false;
        }
        else
        {
            if (loadPng(&(imageLayer.image), filename) == false)
            {
                printf("\nunable to load %s", filename);
            }
            else{
                changeSourceAndUpdateImageLayer(&imageLayer);

                free(imageLayer.image.buffer);

                cnt += 1;
                printf("OK, file %s loaded, cnt: %d\n", filename, cnt);
            }
        }

        usleep(1000);
    }

    //---------------------------------------------------------------------

    if (background > 0)
    {
        destroyBackgroundLayer(&backgroundLayer);
    }


    //---------------------------------------------------------------------

    result = vc_dispmanx_display_close(display);
    assert(result == 0);

    //---------------------------------------------------------------------

    return 0;
}

