// code.js

"use strict";

var workspace;

function init() {
    toolbox = document.getElementById('toolbox');
   
    workspace = Blockly.inject('blocklyDiv',
			       { media: './blockly/media/',
				 toolbox: toolbox } );
}
    
function run() {
    var python_code = Blockly.Python.workspaceToCode(workspace);

    var formData = new FormData();
    var blob = new Blob([python_code], { type: "text/x-python"});
    formData.append('file', blob, "blockly.py");

    var request = new XMLHttpRequest();
    request.onreadystatechange = function() { 
        if (request.readyState == 4 && request.status == 200)
	    alert("Upload successful");
    }

    request.open( "POST", "/", true );

    request.setRequestHeader("Cache-Control", "no-cache");
    request.send( formData );
}

window.addEventListener('load', init);
