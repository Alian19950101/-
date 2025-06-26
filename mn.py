
AttributeError: 'Updater' object has no attribute '_Updater__polling_cleanup_cb' and no __dict__ for setting new attributes
==> Exited with status 1
==> Common ways to troubleshoot your deploy: https://render.com/docs/troubleshooting-deploys
==> Running 'python mn.py'
Traceback (most recent call last):
  File "/opt/render/project/src/mn.py", line 197, in <module>
    asyncio.run(main())
    ~~~~~~~~~~~^^^^^^^^
  File "/usr/local/lib/python3.13/asyncio/runners.py", line 195, in run
    return runner.run(main)
           ~~~~~~~~~~^^^^^^
  File "/usr/local/lib/python3.13/asyncio/runners.py", line 118, in run
    return self._loop.run_until_complete(task)
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  File "/usr/local/lib/python3.13/asyncio/base_events.py", line 725, in run_until_complete
    return future.result()
           ~~~~~~~~~~~~~^^
  File "/opt/render/project/src/mn.py", line 190, in main
    app = Application.builder().token(TOKEN).build()
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/telegram/ext/_applicationbuilder.py", line 298, in build
    updater = Updater(bot=bot, update_queue=update_queue)
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/telegram/ext/_updater.py", line 126, in __init__
    self.__polling_cleanup_cb: Optional[Callable[[], Coroutine[Any, Any, None]]] = None
    ^^^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: 'Updater' object has no attribute '_Updater__polling_cleanup_cb' and no __dict__ for setting new attributes
