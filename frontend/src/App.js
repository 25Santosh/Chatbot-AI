import React, { useState } from "react";
import { Container, TextField, Button, Typography } from "@mui/material";
import axios from "axios";

function App() {
  const [query, setQuery] = useState("");
  const [response, setResponse] = useState("");

  const handleQuery = async () => {
    try {
      const res = await axios.get("http://127.0.0.1:8000/chatbot/", {
        params: { supplier_id: query },
      });
  
      setResponse(JSON.stringify(res.data, null, 2));
    } catch (error) {
      console.error("Error fetching data:", error);
      if (error.response) {
        setResponse(`Server responded with: ${error.response.status} - ${error.response.data}`);
      } else if (error.request) {
        setResponse("No response from server. Possible CORS or server issue.");
      } else {
        setResponse("Request setup error: " + error.message);
      }
    }
  };
  
  

  return (
    <Container maxWidth="sm" style={{ marginTop: "2rem" }}>
      <Typography variant="h4" gutterBottom>
        AI Chatbot
      </Typography>
      <TextField
        label="Enter Supplier ID, Brand, or Product Name"
        variant="outlined"
        fullWidth
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        margin="normal"
      />
      <Button variant="contained" color="primary" fullWidth onClick={handleQuery}>
        Send Query
      </Button>
      {response && (
        <pre
          style={{
            background: "#f4f4f4",
            padding: "10px",
            marginTop: "1rem",
            borderRadius: "5px",
            overflowX: "auto",
          }}
        >
          {response}
        </pre>
      )}
    </Container>
  );
}

export default App;
