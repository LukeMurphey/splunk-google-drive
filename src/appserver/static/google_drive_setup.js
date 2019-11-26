
require(['jquery','underscore','splunkjs/mvc', 'jquery', 'splunkjs/mvc/simplesplunkview', 'util/splunkd_utils', 'splunkjs/mvc/simplexml/ready!'],
	function($, _, mvc, $, SimpleSplunkView, splunkd_utils){
		
	    // Define the setup view class
	    var GoogleDriveSetupView = SimpleSplunkView.extend({
	        className: "GoogleDriveSetupView",
	        
	        defaults: {
	        	filename: null,
	        	service_account_email: null
	        },
	        
	        events: {
	        	"click #choose-import-file" : "chooseImportFile",
	        	"change #import-file-input" : "handleUploadedFile" //handleUploadedFile
	        },
	        
	        initialize: function() {
	        	this.options = _.extend({}, this.defaults, this.options);
	        	
	        	this.filename = this.options.filename;
	        	this.service_account_email = this.options.service_account_email;
	        	this.private_key_id = this.options.private_key_id;
	        	
	        	// This keeps around a timeout ID that clears the changed classes so that the animations work
	        	clearChangedClassesTimeoutID = null;
	        	
	        	this.setupDragDropHandlers();
	        },
	        
	        /**
	         * For some reason the backbone handlers don't work.
	         */
	        setupDragDropHandlers: function(){
	        	
	        	// Setup a handler for handling files dropped on the import dialog
	        	drop_zone2 = document.getElementById('drop-zone');
	        	this.setupDragDropHandlerOnElement(drop_zone2);
	        	
	        },
	        
	        /**
	         * Setup drag & drop handlers on the given drop-zone.
	         */
	        setupDragDropHandlerOnElement: function(drop_zone){
	        	
	        	drop_zone.ondragover = function (e) {
	        		e.preventDefault();
	        		e.dataTransfer.dropEffect = 'copy';
	        	}.bind(this);
	        	
	        	drop_zone.ondrop = function (e) {
	        	      e.preventDefault();
	        	      this.handleUploadedFile(e);
	        	      return false;
	        	}.bind(this);
	        },
	        
	        /**
	         * Clear the classes that highlight changes to the UI.
	         */
	        clearChangedClasses: function(){
       		 	$("#service_account_email").removeClass("changed-success");
       		 	$("#private_key_id").removeClass("changed-success");
	        },
	        
	        /**
	         * Set the inputs to indicate success.
	         */
	        showSuccess: function () {
	        	$("#service_account_email").addClass("changed-success");
	        	$("#private_key_id").addClass("changed-success");
	        	
	        	// Clear the existing timeout so that we don't step on each other
	        	if(this.clearChangedClassesTimeoutID){
	        		window.clearTimeout(this.clearChangedClassesTimeoutID);
	        		this.clearChangedClassesTimeoutID = null;
	        	}
	        	
	        	// Make a timeout to clear the changed classes (otherwise, the CSS animation won't re-fire)
	        	this.clearChangedClassesTimeoutID = window.setTimeout(this.clearChangedClasses.bind(this), 3000);
	        },
	        
	        /**
	         * Upload the given file to Splunk
	         */
	        uploadFile: function (file, file_content) {
	        	
	        	var promise = jQuery.Deferred();
	        	
	        	var file_uri = splunkd_utils.fullpath(['/services/data/service_account_keys/key'].join('/'));
	        	var file_name = file.name;

	        	var data = {
	        		'file_name' : file_name,
	        		'file_contents' : file_content
	        	}
	           
	        	jQuery.ajax({
		             url: file_uri,
		     		 data: data,
	        		 type: 'POST',
		             async: false,
		             
		             success: function(result) {
		            	 
		            	 // Save the information about the key
		            	 this.service_account_email = result['service_account_email'];
		            	 this.private_key_id = result['private_key_id'];
		            	 this.filename = result['filename'];
		            	 
		            	 // Update the UI
		            	 this._render();
		            	 this.showSuccess();
		            	 
		            	 console.info("Successfully added a service account key file");
		            	 promise.resolve(file_name);
		             }.bind(this),
		             
		             error: function(jqXHR,textStatus,errorThrown) {
		            	 console.error("Unable to save the file");
		            	 promise.reject("Unable to save the file");
		             }
	        	});

	        	return promise;
	        },
	        
	        /**
	         * Handle the event that occurs when a file is uploaded
	         */
	        handleUploadedFile: function(evt){
	        	
	        	// Stop if the browser doesn't support processing files in Javascript
	        	if(!window.FileReader){
	        		alert("Your browser doesn't support file reading in Javascript; thus, I cannot parse your uploaded file");
	        		return false;
	        	}

	        	var files = [];

	        	// Get the files from an input widget if available
	        	if(evt.target.files && evt.target.files.length > 0){
	        		files = evt.target.files;
	        	}

	        	// Get the files from the drag & drop if available
	        	else if(evt.dataTransfer && evt.dataTransfer.files.length > 0){
	        		files = evt.dataTransfer.files;
	        	}

	        	// Stop if no files where provided (user likely pressed cancel)
	        	if(files.length > 0 ){

	        		// Get the file name
	        		var file_size = files[0].size;

	        		// Check if file is larger than 4MB
	        		if (file_size > 4194304) {
	        			alert("File is larger than 4MB");
	        			return false;
	        		}

	        		// Get a reader so that we can read in the file
	        		var reader = new FileReader();

	        		// Setup an onload handler that will process the file
	        		reader.onload = function(evt) {
	        			
	        			// Stop if the ready state isn't "loaded"
	        			if(evt.target.readyState != 2){
	        				return;
	        			}
	        			
	        			// Stop if the file could not be processed
	        			if(evt.target.error) {
	        				alert("File could not be processed");
	        				return;
	        			}
	        			
	        			// Get the file contents
	        			var file_content = evt.target.result;
	        			
	        			// Upload the file contents
	        			$.when(this.uploadFile(files[0], file_content)).done(function(file_name){
	        				console.info("File successfully uploaded");
	        			});

	        		}.bind(this);

	             	// Start the process of processing file
	             	reader.readAsDataURL(files[0]);
	        	}
	        	else{
	        	   alert("No file object was found");
	        	   return false;
	           	}
	        	
	        	return true;
	        },
	        
	        /**
	         * Open the file dialog to select a file to import.
	         */
	        chooseImportFile: function(){
	        	$("#import-file-input").click();
	        },
	        
	        /**
	         * Import the dropped file.
	         */
	        onDropFile: function(evt){
	        	
	        	console.log("Got a file via drag and drop");
	        	evt.stopPropagation();
	            evt.preventDefault();
	            var files = evt.dataTransfer.files;
	            
	            this.importFile(evt);
	        },
	        
	        /**
	         * Determine if a key is already defined and get information about it if it does.
	         */
	        render: function () {
	        	
	        	var uri = splunkd_utils.fullpath(['/services/data/service_account_keys/key'].join('/'));
	           
	        	jQuery.ajax({
		             url: uri,
		             
		             success: function(result) {
		            	 
		            	// Save the information about the key
		            	 this.service_account_email = result['service_account_email'];
		            	 this.private_key_id = result['private_key_id'];
		            	 this.filename = result['filename'];
		            	 
		            	// Update the UI
		            	 this._render();
		             }.bind(this),
		             
		             error: function(jqXHR,textStatus,errorThrown) {
		            	 alert("Unable to get information about the current service key");
		             }
	        	});
	        },
	        
	        /**
	         * Render the view contents based on the information we know about the key.
	         */
	        _render: function(){
	        	
	        	// Show the parts of the view that show that a key has been loaded
	        	if(this.service_account_email != null){
	        		$('.show_when_no_key').hide();
	        		$('.show_when_with_key').show();
	        		$('#service_account_email').val(this.service_account_email);
	        		$('#private_key_id').val(this.private_key_id);
	        	}
	        	
	        	// Show the parts of the view that show that a key has _not_ been loaded
	        	else{
	        		$('.show_when_no_key').show();
	        		$('.show_when_with_key').hide();
	        		$('#service_account_email').val("");
	        		$('#private_key_id').val("");
	        	}
	        	
	        }
	        
	    });
	    
    	// Make the view instance
    	var setup_view = new GoogleDriveSetupView({
    		'el' : $('#google_drive_setup_view')
    	});
    	
    	// Render the view
    	setup_view.render();
    	
	}
);