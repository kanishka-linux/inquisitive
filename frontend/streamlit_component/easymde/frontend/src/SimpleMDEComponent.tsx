import React, { useEffect, useRef } from "react";
import { ComponentProps, Streamlit } from "streamlit-component-lib";

interface SimpleMDEProps {
  value: string;
  height: number;
}

const SimpleMDEComponent: React.FC<ComponentProps<SimpleMDEProps>> = (props) => {
  const { value = "", height = 500 } = props.args;
  const editorRef = useRef<HTMLTextAreaElement>(null);
  const editorInstance = useRef<any>(null);
  const initialized = useRef<boolean>(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Add CSS to fix scrollbars, toolbar, and side-by-side mode
    const style = document.createElement('style');
    style.textContent = `
      /* Container styling */
      .EasyMDEContainer {
        display: flex;
        flex-direction: column;
        width: 100% !important;
      }
      
      /* Make the toolbar match textarea styling */
      .EasyMDEContainer .editor-toolbar {
        position: sticky;
        top: 0;
        z-index: 10;
        background: white;
        border: 1px solid #ccc;
        border-bottom: 1px solid #ccc;;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
        opacity: 1 !important;
        padding: 6px;
      }
      
      /* Ensure toolbar is always visible on hover */
      .EasyMDEContainer:hover .editor-toolbar {
        opacity: 1 !important;
      }
      
      /* Fix editor styling to match textarea */
      .EasyMDEContainer .CodeMirror {
        height: ${height - 40}px !important;
        min-height: ${height - 40}px !important;
        max-height: ${height - 40}px !important;
        overflow-y: auto !important;
        border: 1px solid #ccc;
        border-bottom-left-radius: 4px;
        border-bottom-right-radius: 4px;
        font-family: inherit;
      }
      
      .EasyMDEContainer .CodeMirror-scroll {
        min-height: ${height - 40}px !important;
        max-height: ${height - 40}px !important;
        overflow-y: auto !important;
      }
      
      /* Preview styling */
      .EasyMDEContainer .editor-preview-side {
        height: ${height - 40}px !important;
        overflow-y: auto !important;
        top: 40px !important;
        background: white;
        border: 1px solid #ccc;
        border-top: none;
        border-bottom-right-radius: 4px;
      }
      
      /* Fix side-by-side mode */
      .EasyMDEContainer.sided {
        display: flex;
        flex-direction: column;
        width: 100% !important;
      }
      
      .EasyMDEContainer.sided .CodeMirror-sided {
        width: 50% !important;
        float: left;
        border-right: none;
        border-bottom-right-radius: 0;
      }
      
      .EasyMDEContainer.sided .editor-preview-side {
        width: 50% !important;
        float: right;
        border-left: 1px solid #ddd;
        border-bottom-left-radius: 0;
      }
      
      /* Fix editor-preview-wrapper in side-by-side mode */
      .EasyMDEContainer.sided .editor-preview-active-side {
        display: block !important;
      }
      
      /* Fix fullscreen mode */
      .EasyMDEContainer.fullscreen {
        z-index: 9999 !important;
      }
      
      .EasyMDEContainer.fullscreen .editor-toolbar {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        border-radius: 0;
      }
      
      .EasyMDEContainer.fullscreen .CodeMirror {
        border-radius: 0;
        border: none;
        margin-top: 40px;
      }
      
      .EasyMDEContainer.fullscreen.sided .editor-preview-side {
        border-radius: 0;
        border: none;
        border-left: 1px solid #ddd;
      }
    `;
    document.head.appendChild(style);

    Streamlit.setComponentReady();
    
    const initEditor = () => {
      if (editorRef.current && !initialized.current && window.EasyMDE) {
        try {
          console.log("Initializing EasyMDE...");
          const editor = new window.EasyMDE({
            element: editorRef.current,
            initialValue: value,
            autofocus: true,
            spellChecker: false,
            toolbar: [
              "bold",
              "italic",
              "strikethrough",
              "heading", "|", 
              "quote",
              "code",
              "clean-block", "|",
              "unordered-list",
              "ordered-list", "|",
              "link",
              "image", "|",
              "table", "|",
              "undo",
              "redo", "|",
              "preview",
              "side-by-side",
              "fullscreen", "|",
              "guide"
            ],
            status: ["lines", "words"],
            // Set fixed height for the editor (accounting for toolbar)
            minHeight: `${height - 40}px`,
            maxHeight: `${height - 40}px`,
            // Prevent toolbar from disappearing
            toolbarSticky: true,
            // Improve side-by-side mode
            sideBySideFullscreen: false,
          });

          // Force CodeMirror to use the correct height and show scrollbars
          editor.codemirror.setSize(null, height - 40);
          
          // Handle side-by-side mode toggle
          const handleSideBySideToggle = () => {
            setTimeout(() => {
              const container = document.querySelector('.EasyMDEContainer');
              if (container && container.classList.contains('sided')) {
                // Ensure proper width for side-by-side elements
                const cmElement = editor.codemirror.getWrapperElement();
                const previewElement = document.querySelector('.editor-preview-side');
                
                if (cmElement && previewElement) {
                  cmElement.style.width = '50%';
                  (previewElement as HTMLElement).style.width = '50%';
                }
              }
            }, 10);
          };
          
          // Add event listener for side-by-side button
          const sideBySideButton = document.querySelector('.fa-columns');
          if (sideBySideButton) {
            sideBySideButton.addEventListener('click', handleSideBySideToggle);
          }

          editor.codemirror.on("change", () => {
            const currentValue = editor.value();
            Streamlit.setComponentValue(currentValue);
          });

          editorInstance.current = editor;
          initialized.current = true;
          console.log("EasyMDE initialized successfully");
        } catch (error) {
          console.error("Error initializing EasyMDE:", error);
        }
      } else if (!window.EasyMDE) {
        console.error("EasyMDE not found in window object");
      }
    };

    // Try to initialize immediately
    initEditor();
    
    // Also try after a short delay to ensure DOM and scripts are loaded
    const timeoutId = setTimeout(initEditor, 500);
    
    // Set the frame height
    Streamlit.setFrameHeight(height);
    
    return () => {
      clearTimeout(timeoutId);
      document.head.removeChild(style);
      
      // Remove event listener for side-by-side button
      const sideBySideButton = document.querySelector('.fa-columns');
      if (sideBySideButton) {
        sideBySideButton.removeEventListener('click', () => {});
      }
      
      if (editorInstance.current) {
        try {
          editorInstance.current.toTextArea();
        } catch (e) {
          console.error("Error cleaning up EasyMDE:", e);
        }
        editorInstance.current = null;
        initialized.current = false;
      }
    };
  }, [value, height]);

  return (
    <div 
      ref={containerRef}
      style={{ 
        height: `${height}px`, 
        width: "100%",
        overflow: "hidden"
      }}
    >
      <textarea 
        ref={editorRef} 
        defaultValue={value} 
        style={{ 
          display: "block", 
          width: "100%",
          height: "100%",
          padding: "8px",
          border: "1px solid #ccc",
          borderRadius: "4px"
        }} 
      />
    </div>
  );
};

export default SimpleMDEComponent;
