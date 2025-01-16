Output demo.gif

Require echo

Set Shell "fish"
Set FontSize 16
Set Width 1200
Set Height 600

Type "cli build todo.yaml" Sleep 1s Enter
Sleep 5s
Type "./todo -h" Sleep 500ms Enter
Sleep 4s
Type "./todo create" Sleep 500ms Enter
Sleep 1s 
Type "mytodo" Sleep 1s Enter
Sleep 1s
Type "mytodo" Sleep 1s Enter
Sleep 3s
Type "./todo tasks mytodo" Sleep 500ms Enter
Sleep 3s
Type './todo add mytodo "To code!"' Sleep 1s Enter
Sleep 2s
Type "./todo tasks mytodo" Sleep 500ms Enter
Sleep 5s

