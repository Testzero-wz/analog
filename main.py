from analog.bin.controller.controller import Controller
import os, sys
import traceback

if sys.version_info < (3, 5):
    sys.stdout.write("Requires Python 3.5 or higher ")
    sys.exit(1)


def main():
    controller = None
    try:
        path = os.path.dirname(os.path.realpath(__file__))
        controller = Controller(path)
        controller.mainloop()
    except KeyboardInterrupt:
        print("User abort")
    except Exception as e:
        traceback.print_exc()
        print(e)
    finally:
        if controller is not None:
            controller.update_thread_stop_flag = True
            controller.output.print_info("Waiting for update thread exit...")
            controller.update_thread.join()


if __name__ == "__main__":
    main()
