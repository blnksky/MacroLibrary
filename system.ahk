#Include  common.ahk
#Include  structures.ahk

; architecture utils and reqs
class Sys {
    static enabled := false
    static appId := ""
    static inputs := Map()
    static keys := Map()
    static binds := Map()
    static build := Map()
    static hotkeys := HotkeyHandler

    static toggleEvent := Event((enabled) => [])
    static toggle(enabled := ""){
        this.enabled := enabled = "" ? !this.enabled : enabled

        if(!WinActive(this.appId)){
            this.enabled := false
        }
        
        for key , bind in this.hotkeys.dict["*"]{
            if(
                key = normalizeInput(this.keys["base"]["manualToggle"])
            ){
                this.hotkeys.toggle(key , true)
                continue
            }

            this.hotkeys.toggle(key , this.enabled)
        }

        this.toggleEvent(this.enabled)
    }

    static initialize(inputs , keys , binds , build){
        this.inputs := inputs
        this.keys := keys
        this.binds := binds
        this.build := build

        ; get macros
        register(id){
            key := path(this.keys , id)
            bind := path(this.binds , id)
            if(key = "" or bind = ""){
                return
            }
            this.hotkeys.register(key , bind)
        }
        
        iterate(file , id := ""){
            if(file = ""){
                return
            }
            
            idprefix := id = "" ? "" : id . "."

            if(Type(file) = "Map"){
                for i , f in file{
                    iterate(f , idprefix . i)
                }
                return
            }else if(Type(file) = "Array"){
                for e in file{
                    iterate(e , id)
                }
                return
            }else if(Type(file) = "String"){
                id := idprefix . file
            }else if(file != 1){
                return
            }

            file := path(this.keys , id)
            if(file = ""){
                return
            }
            
            if(Type(file) = "Map"){
                for i , _ in path(this.keys , id){
                    register(id . "." . i)
                }
            }else{
                register(id)
            }
        }
        iterate(this.build)

        this.hotkeys.initialize()
        this.hotkeys.toggle(this.keys["base"]["manualToggle"] , true)
    }

    static exit(){
        this.toggle(false)
        ExitApp()
    }
}

class HotkeyHandler {
    static dict := Map(
        "*" , Map(),
        "+" , Map(),
        "!" , Map(),
        "^" , Map(),
        "~" , Map(),
    )
    static inputStates := Map()

    static register(id , bind){
        if(id = "" or bind = ""){
            return
        }

        modifier := SubStr(id , 1 , 1)
        if(
            !this.dict.Has(modifier)
            or modifier = SubStr(normalizeInput(id) , 1 , 1)
        ){
            modifier := "*"
        }

        id := normalizeInput(id)
        this.dict[modifier].Set(id , bind)
    }

    static toggle(key , enabled){
        Hotkey(hotkeyNormalize(key) , enabled ? "On" : "Off" , "I1")
    }

    static initialize(){
        ; pass-through hotkeys
        for id , bind in this.dict["~"]{
            found := false
            for modifier , f in this.dict{
                if(modifier = "~" or !f.Has(id)){
                    continue
                }
                found := true
            }

            if(found){
                this.dict["~"].Delete(id)

                t := bind
                bind := (key) => [
                    send(id . " Down")
                    t(id)
                    KeyWait(id)
                    send(id . " Up")
                ]
            }
            this.dict["*"].Set(id , bind)
        }

        for modifier , f in this.dict{
            if(modifier = "*"){
                continue
            }

            for id , bind in f{
                id := normalizeInput(id)

                if(this.dict["*"].Has(id)){
                    continue
                }

                this.register(id , (id) => [
                    send(id . " Down")
                    KeyWait(id)
                    send(id . " Up")
                ])
            }
        }

        ; unified hotkeys
        for id , bind in this.dict["*"]{
            id := normalizeInput(id)
            this.inputStates[id] := 0

            function(id){
                id := normalizeInput(id)
                
                if(!WinActive(Sys.appId)){
                    Sys.toggle(false)
                    return
                }

                if(this.inputStates[id] > 0){
                    return
                }

                if(!this.customHandler(id)){
                    Send(id . " Down")
                    inputYield(id)
                    Send(id . " Up")
                    return
                }

                macro := ""

                if(GetKeyState("LAlt" , "P") and this.dict["!"].Has(id)){
                    macro := this.dict["!"][id]
                }if(GetKeyState("LControl" , "P") and this.dict["^"].Has(id)){
                    macro := this.dict["^"][id]
                }if(GetKeyState("Shift" , "P") and this.dict["+"].Has(id)){
                    macro := this.dict["+"][id]
                }
                
                if(macro = ""){
                    macro := this.dict["*"][id]
                }

                this.inputStates[id] += 2
                macro(id)
                
                this.inputStates[id] -= 1
                inputYield(id)
                
                this.inputStates[id] -= 1
            }

            Hotkey(hotkeyNormalize(id) , function , "Off")
        }
    }

    static customHandler := (self , id) => 1
}

hotkeyNormalize(id){
    return "$*" . (Sys.hotkeys.dict["~"].Has(normalizeInput(id)) ? "~" : "") . id
}