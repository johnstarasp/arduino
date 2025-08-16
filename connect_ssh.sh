#!/usr/bin/expect -f

set timeout 30
spawn ssh jstaras@192.168.1.48

expect {
    "yes/no" {
        send "yes\r"
        exp_continue
    }
    "password:" {
        send "Saskatouraw1!\r"
    }
}

expect "$ "
send "cd /repos/arduino\r"
expect "$ "
send "ls -la\r"
expect "$ "

# Keep the session open
interact