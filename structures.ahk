#Include common.ahk

class Event{
    func := (args*) => []
    connections := Map()

    class Connection{
        func := (args*) => []

        __New(event := Event() , f := (args*) => []){
            this.event := event
            this.func := (args*) => f(trimArray(args , f.MaxParams)*)
            event.connections.Set(this , 1)
        }

        Call(self , args*){
            f := this.func
            f(args*)
        }

        static Once(e := Event() , f := (args*) => []){
            con := Event.Connection(e)
            con.func := (args*) => [
                f(trimArray(args , f.MaxParams)*)
                con.disconnect()
            ]
            return con
        }

        disconnect(){
            this.event.disconnect(this)
        }
    }

    __New(f := (args*) => []){
        this.func := (args*) => f(trimArray(args , f.MaxParams)*)
    }

    Call(args*){
        f := this.func
        f(args*)
        for c , _ in this.connections{
            c(args*)
        }
    }

    connect(f){
        return Event.Connection(this , f)
    }

    once(f){
        return Event.Connection.Once(this , f)
    }

    disconnect(con){
        this.connections.Delete(con)
    }
}

class state{
    static last := 0

    static Call(buffer := 0){
        dt := this.last - now()
        res := dt <= buffer
        if(res and dt > 0){
            Sleep(dt)
        }
        return res
    }

    static pend(duration := 0){
        cid := now() + duration
        if(cid < this.last){
            return 0
        }

        this.last := cid
        return cid
    }

    static clear(sid := 0){
        if(this.last != sid){
            return 0
        }
        this.last := now()
        return 1
    }

    static yield(duration := 0){
        cid := (duration > 0) ? this.pend(duration) : 0
        Sleep(this.last - now())
        return cid
    }
}

class Action{
    class := Action
    static buffer := 0
    
    duration := 0
    last := 0
    launch := (self , args*) => []
    
    Call(args*){
        if(!state(this.class.buffer)){
            return 0
        }
        
        this.active(1)
        cid := state.pend(this.duration)
        if(cid = 0){
            return 0
        }

        this.last := cid
        delay(() => this.cancel() , this.duration)
        this.launch(args*)
        
        return cid
    }
    
    static activeAction := ""
    active(state := ""){
        action := this.class.activeAction
        if(state = "" or (action != "" and action != this)){
            return action = "" ? 0 : action
        }

        this.class.activeAction := state ? this : ""

        return this.active()
    }

    cancel(){
        if(this.last - now() <= this.class.buffer){
            return 0
        }

        this.active(0)
        state.clear(this.last)

        return 1
    }

    cancelled(cid := 0){
        return cid != this.last
    }

    __New(duration := 0 , launch := (id , args*) => []){
        this.duration := duration
        this.launch := launch
    }
}