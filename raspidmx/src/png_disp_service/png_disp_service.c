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

char watch_dir[1024];
char img_path[1024];
char screen_notify_name[1024];
char hk_notify_name[1024];
char exit_notify_path[1024];

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

    FILE *fp;
    fp = fopen( exit_notify_path, "w");
    if (fp == NULL) {
        printf ("Cannot Open file %s, errno = %d\n", exit_notify_path, errno);
    }

    fclose (fp);
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

    char* tmp;
    strcpy (img_path, argv[1]);

    tmp = dirname(argv[1]);
    strcpy (watch_dir, tmp);

    char img_path_[1024];
    strcpy (img_path_, img_path);
    char* basename_;
    basename_ = basename(img_path_);
    strcpy (screen_notify_name, basename_);
    strcat (screen_notify_name, ".screen.log");

    strcpy (hk_notify_name, basename_);
    strcat (hk_notify_name, ".hk.log");

    strcpy (exit_notify_path, img_path);
    strcat (exit_notify_path, ".exit.log");


    printf("\n%s\n", img_path);
    printf("\n%s\n", watch_dir);
    printf("\n%s\n", screen_notify_name);
    printf("\n%s\n", hk_notify_name);
    printf("\n%s\n", exit_notify_path);

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


    IMAGE_LAYER_T imageLayer;


    //---------------------------------------------------------------------
    while(run)
    {
        usleep(1000000);
        if (loadPng(&(imageLayer.image), img_path) == false)
        {
            fprintf(stderr, "unable to load %s\n", img_path);
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

    int length;
    int fd;
    int wd;
    char buffer[EVENT_BUF_LEN];

    //--------------- creating the INOTIFY instance ---------------
    fd = inotify_init();

    /*checking for error*/
    if ( fd < 0 )
    {
        perror( "inotify_init" );
    }

    //--------- adding the "/home/pi/Desktop/App" directory into watch list.
    wd = inotify_add_watch( fd, watch_dir, IN_CLOSE_WRITE | IN_OPEN );

    int cnt = 0;

    while (run)
    {
        bool has_finish_update = false;
        bool notify_was_opened = false;
        bool notify_was_closed = false;

        // read to determine the event change happens on "/home/pi/Desktop/App" directory.
        // Actually this read blocks until the change event occurs

        length = read( fd, buffer, EVENT_BUF_LEN );

        if ( length < 0 )
        {
            perror( "inotify read error" );
        }

        int  i = 0;

        // actually read return the list of change events happens.
        // Here, read the change event one by one and process it accordingly
        while ( i < length && run)
        {
            int r = 1, r2 = 1;
            struct inotify_event *event = ( struct inotify_event * ) &buffer[ i ];
            if ( event->len )
            {
                if ( event->mask & IN_OPEN )
                {
                    if ( !(event->mask & IN_ISDIR) )
                    {
                        r = strcmp(screen_notify_name, event->name);
                        r2 = strcmp(hk_notify_name, event->name);
                        if (r == 0 || r2 == 0)
                        {
                            notify_was_opened = true;
                            //printf( "File %s was opened.\n", event->name );
                        }
                    }

                }
                else if ( event->mask & IN_CLOSE_WRITE )
                {
                    if ( !(event->mask & IN_ISDIR) )
                    {
                        r = strcmp(screen_notify_name, event->name);
                        r2 = strcmp(hk_notify_name, event->name);
                        if (r == 0 || r2 == 0)
                        {
                            notify_was_closed = true;
                            //printf( "File %s was closed.\n", event->name );
                        }
                    }
                }
            }

            i += EVENT_SIZE + event->len;
        }


        //has_finish_update = notify_was_closed & notify_was_opened;

        has_finish_update = notify_was_opened;

        if(has_finish_update)
        {
            if (loadPng(&(imageLayer.image), img_path) == false)
            {
                printf("unable to load %s\n", img_path);
            }
            else{

                changeSourceAndUpdateImageLayer(&imageLayer);

                free(imageLayer.image.buffer);

                cnt += 1;
                printf("Loaded file %s  cnt %d\n", img_path, cnt);
                usleep(2500000);
            }
        }
        usleep(10);
    }

     // removing the directory from the watch list
    inotify_rm_watch( fd, wd );

    // closing the INOTIFY instance
    close( fd );

    //---------------------------------------------------------------------

    keyboardReset();

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

