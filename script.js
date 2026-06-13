const kingdoms=[

{
name:"Cascade",
image:"assets/Cascade.png"
},

{
name:"Sand",
image:"assets/Sand.png"
},

{
name:"Lake",
image:"assets/Lake.png"
},

{
name:"Wooded",
image:"assets/Wooded.png"
},

{
name:"Cloud",
image:"assets/Cloud.png"
},

{
name:"Lost",
image:"assets/Lost.png"
},

{
name:"Metro",
image:"assets/Metro.png"
},

{
name:"Snow",
image:"assets/Snow.png"
},

{
name:"Seaside",
image:"assets/Seaside.png"
},

{
name:"Luncheon",
image:"assets/Luncheon.png"
},

{
name:"Ruined",
image:"assets/Ruined.png"
},

{
name:"Bowser",
image:"assets/Bowser.png"
}

];

const tracker=document.getElementById("tracker");

let state={};

function save(){

    localStorage.setItem("tracker",JSON.stringify(state));

}

function load(){

    let s=localStorage.getItem("tracker");

    if(s){

        state=JSON.parse(s);

    }

}

load();

kingdoms.forEach(k=>{

    if(!state[k.name]){

        state[k.name]={

            count:0,

            max:"?"

        };

    }

    const row=document.createElement("div");

    row.className="row";

    const img=document.createElement("img");

    img.src=k.image;

    row.appendChild(img);

    const minus=document.createElement("button");

    minus.textContent="-";

    row.appendChild(minus);

    const counter=document.createElement("div");

    counter.className="counter";

    row.appendChild(counter);

    const plus=document.createElement("button");

    plus.textContent="+";

    row.appendChild(plus);

    const max=document.createElement("input");

    max.placeholder="?";

    max.value=state[k.name].max==="?"?"":state[k.name].max;

    row.appendChild(max);

    function update(){

        counter.textContent=

            state[k.name].count+

            " / "+

            state[k.name].max;

        save();

    }

    plus.onclick=()=>{

        state[k.name].count++;

        update();

    };

    minus.onclick=()=>{

        if(state[k.name].count>0)

            state[k.name].count--;

        update();

    };

    max.oninput=()=>{

        state[k.name].max=

            max.value==""?

            "?":

            parseInt(max.value);

        update();

    };

    update();

    tracker.appendChild(row);

});
