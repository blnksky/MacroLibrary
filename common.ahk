; input handling
{
    send(id){
        SendInput("{" . normalizeInput(id) . "}")
    }
    
    isDown(id){
        return GetKeyState(id , "P")
    }
    
    inputYield(id , timeout := 0){
        if(!isDown(id)){
            return 1
        }
    
        return KeyWait(
            id,
            timeout > 0 ? ("T" . (timeout / 1000)) : ""
        )
    }
    
    normalizeInput(id){
        return RegExReplace(id , "\$|\~|\*|\+|\#|\^|\!|\{|\}")
    }
}

; time and thread handling
{
    now(){
        return A_TickCount
    }

    SetTimerDeprecated := SetTimer
    delay(callback := () => [] , delay := 0){
        delay := delay <= 0 ? 10 : delay
        SetTimerDeprecated(callback , -delay , 10)
    }
}

; structural
{
    trimArray(arr := [] , length := 0){
        i := 0
        args := []
        
        while i < length{
            i++
            args.Push(arr.Has(i) ? arr.Get(i) : "")
        }

        return args
    }

    path(file , path){
        for _ , path in StrSplit(path , "."){
            if(!file.Has(path)){
                return ""
            }
            file := file[path]
        }
    
        return file
    }
}