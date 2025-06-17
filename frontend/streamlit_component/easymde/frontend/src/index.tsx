import React from "react";
import ReactDOM from "react-dom";
import SimpleMDEComponent from "./SimpleMDEComponent";
import { withStreamlitConnection } from "streamlit-component-lib";
import "easymde/dist/easymde.min.css";

// Wrap the component with the Streamlit connection
const ConnectedComponent = withStreamlitConnection(SimpleMDEComponent);

// Render the component
ReactDOM.render(
  <React.StrictMode>
    <ConnectedComponent />
  </React.StrictMode>,
  document.getElementById("root")
);
