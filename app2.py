import dash
from dash import dcc, html, Input, Output, State, callback, callback_context
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
import base64
import io
import tempfile
import os
import json
import google.generativeai as genai
from datetime import datetime
import PyPDF2
import requests
from bs4 import BeautifulSoup
import re
import urllib.parse

# Initialize the Dash app with a bootstrap theme
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.FLATLY],
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
    suppress_callback_exceptions=True  # Add this line to suppress callback exceptions
)
server = app.server
app.title = "AI Cover Letter Generator"

# Define card styles
card_style = {
    "borderRadius": "15px",
    "boxShadow": "0px 4px 12px rgba(0, 0, 0, 0.1)",
    "padding": "20px",
    "marginBottom": "20px",
    "backgroundColor": "#ffffff",
}

button_style = {
    "borderRadius": "8px",
    "fontWeight": "bold",
    "boxShadow": "0px 2px 4px rgba(0, 0, 0, 0.1)",
}

input_style = {
    "borderRadius": "8px",
    "border": "1px solid #ddd",
    "padding": "10px",
}

# Layout
app.layout = dbc.Container(
    [
        # Header
        dbc.Row(
            [
                dbc.Col(
                    html.Div(
                        [
                            html.H1(
                                "AI Cover Letter Generator",
                                className="text-center text-primary mb-3",
                                style={"fontWeight": "bold"},
                            ),
                            html.P(
                                "Upload your existing cover letter and job description to generate a tailored cover letter",
                                className="text-center text-muted",
                            ),
                        ],
                        style={"paddingTop": "30px", "paddingBottom": "20px"},
                    ),
                    width=12,
                ),
            ]
        ),
        
        # API Key Configuration Section
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader("Google AI API Configuration", className="text-primary fw-bold"),
                            dbc.CardBody(
                                [
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                dbc.Input(
                                                    id="api-key",
                                                    type="password",
                                                    placeholder="Enter Google AI Studio API Key",
                                                    style=input_style,
                                                ),
                                                md=9,
                                            ),
                                            dbc.Col(
                                                dbc.Button(
                                                    "Save Key",
                                                    id="save-api-key",
                                                    color="success",
                                                    className="w-100",
                                                    style=button_style,
                                                ),
                                                md=3,
                                            ),
                                        ]
                                    ),
                                    html.Div(id="api-key-status", className="mt-2"),
                                ]
                            ),
                        ],
                        style=card_style,
                    ),
                    width=12,
                )
            ]
        ),
        
        # Main content
        dbc.Row(
            [
                # Job description column
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    "Job Description", 
                                    className="text-primary fw-bold"
                                ),
                                dbc.CardBody(
                                    [
                                        dcc.Tabs(
                                            id="job-description-tabs",
                                            value="manual-tab",
                                            className="mb-3",
                                            children=[
                                                dcc.Tab(
                                                    label="Manual Entry",
                                                    value="manual-tab",
                                                    children=[
                                                        dcc.Textarea(
                                                            id="job-description",
                                                            placeholder="Paste the job description here...",
                                                            style={
                                                                "width": "100%",
                                                                "height": "250px",
                                                                "borderRadius": "8px",
                                                                "padding": "10px",
                                                                "marginTop": "10px",
                                                            },
                                                        ),
                                                    ],
                                                ),
                                                dcc.Tab(
                                                    label="URL Import",
                                                    value="url-tab",
                                                    children=[
                                                        dbc.Input(
                                                            id="job-url",
                                                            type="url",
                                                            placeholder="Enter job listing URL...",
                                                            style={"marginTop": "10px", **input_style},
                                                        ),
                                                        dbc.Button(
                                                            [html.I(className="fas fa-globe me-2"), "Extract from URL"],
                                                            id="extract-url-btn",
                                                            color="primary",
                                                            className="mt-3 w-100",
                                                            style=button_style,
                                                        ),
                                                        html.Div(id="url-extraction-status", className="mt-2"),
                                                    ],
                                                ),
                                            ],
                                        ),
                                        dbc.Button(
                                            [html.I(className="fas fa-upload me-2"), "Upload Job Description"],
                                            id="upload-job-btn",
                                            color="secondary",
                                            className="mt-3 me-2",
                                            style=button_style,
                                        ),
                                        dcc.Upload(
                                            id="upload-job",
                                            children=[],
                                            style={"display": "none"},
                                            multiple=False,
                                        ),
                                    ]
                                ),
                            ],
                            style=card_style,
                        ),
                    ],
                    md=6,
                ),
                
                # Original cover letter column
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    "Your Original Cover Letter", 
                                    className="text-primary fw-bold"
                                ),
                                dbc.CardBody(
                                    [
                                        dcc.Tabs(
                                            id="cover-letter-tabs",
                                            value="manual-cover-tab",
                                            className="mb-3",
                                            children=[
                                                dcc.Tab(
                                                    label="Manual Entry",
                                                    value="manual-cover-tab",
                                                    children=[
                                                        dcc.Textarea(
                                                            id="original-cover-letter",
                                                            placeholder="Paste your existing cover letter here...",
                                                            style={
                                                                "width": "100%",
                                                                "height": "250px",
                                                                "borderRadius": "8px",
                                                                "padding": "10px",
                                                                "marginTop": "10px",
                                                            },
                                                        ),
                                                    ],
                                                ),
                                                dcc.Tab(
                                                    label="PDF Import",
                                                    value="pdf-tab",
                                                    children=[
                                                        dcc.Upload(
                                                            id="pdf-upload",
                                                            children=html.Div([
                                                                html.I(className="fas fa-file-pdf fa-2x text-danger mb-2"),
                                                                html.P("Drag and Drop or Click to Upload PDF Cover Letter"),
                                                            ]),
                                                            style={
                                                                "width": "100%",
                                                                "height": "200px",
                                                                "lineHeight": "60px",
                                                                "borderWidth": "1px",
                                                                "borderStyle": "dashed",
                                                                "borderRadius": "8px",
                                                                "textAlign": "center",
                                                                "padding": "30px 0",
                                                                "marginTop": "10px",
                                                            },
                                                            multiple=False,
                                                        ),
                                                        html.Div(id="pdf-upload-status", className="mt-3"),
                                                    ],
                                                ),
                                            ],
                                        ),
                                        dbc.Button(
                                            [html.I(className="fas fa-upload me-2"), "Upload Cover Letter"],
                                            id="upload-letter-btn",
                                            color="secondary",
                                            className="mt-3 me-2",
                                            style=button_style,
                                        ),
                                        dcc.Upload(
                                            id="upload-letter",
                                            children=[],
                                            style={"display": "none"},
                                            multiple=False,
                                        ),
                                    ]
                                ),
                            ],
                            style=card_style,
                        ),
                    ],
                    md=6,
                ),
            ]
        ),
        
        # Generation controls
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader("Generation Settings", className="text-primary fw-bold"),
                            dbc.CardBody(
                                [
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    html.Label("Tone:"),
                                                    dcc.Dropdown(
                                                        id="tone-dropdown",
                                                        options=[
                                                            {"label": "Professional", "value": "professional"},
                                                            {"label": "Enthusiastic", "value": "enthusiastic"},
                                                            {"label": "Confident", "value": "confident"},
                                                            {"label": "Friendly", "value": "friendly"},
                                                            {"label": "Formal", "value": "formal"},
                                                        ],
                                                        value="professional",
                                                        clearable=False,
                                                        style={"borderRadius": "8px"},
                                                    ),
                                                ],
                                                md=4,
                                            ),
                                            dbc.Col(
                                                [
                                                    html.Label("Length:"),
                                                    dcc.Dropdown(
                                                        id="length-dropdown",
                                                        options=[
                                                            {"label": "Concise", "value": "concise"},
                                                            {"label": "Moderate", "value": "moderate"},
                                                            {"label": "Detailed", "value": "detailed"},
                                                        ],
                                                        value="moderate",
                                                        clearable=False,
                                                        style={"borderRadius": "8px"},
                                                    ),
                                                ],
                                                md=4,
                                            ),
                                            dbc.Col(
                                                [
                                                    html.Label("Focus:"),
                                                    dcc.Dropdown(
                                                        id="focus-dropdown",
                                                        options=[
                                                            {"label": "Skills Match", "value": "skills"},
                                                            {"label": "Experience", "value": "experience"},
                                                            {"label": "Culture Fit", "value": "culture"},
                                                            {"label": "Balanced", "value": "balanced"},
                                                        ],
                                                        value="balanced",
                                                        clearable=False,
                                                        style={"borderRadius": "8px"},
                                                    ),
                                                ],
                                                md=4,
                                            ),
                                        ],
                                        className="mb-3",
                                    ),
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                dbc.Button(
                                                    [html.I(className="fas fa-magic me-2"), "Generate Cover Letter"],
                                                    id="generate-btn",
                                                    color="primary",
                                                    size="lg",
                                                    className="w-100",
                                                    style=button_style,
                                                ),
                                                width=12,
                                            ),
                                        ]
                                    ),
                                ]
                            ),
                        ],
                        style=card_style,
                    ),
                    width=12,
                )
            ]
        ),
        
        # Processing indicator
        dbc.Row(
            [
                dbc.Col(
                    html.Div(
                        [
                            dbc.Spinner(color="primary", size="lg"),
                            html.P("Generating your personalized cover letter...", className="text-center text-muted mt-2"),
                        ],
                        id="loading-indicator",
                        style={"display": "none", "textAlign": "center", "paddingTop": "20px", "paddingBottom": "20px"},
                    ),
                    width=12,
                ),
            ]
        ),
        
        # Generated cover letter
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader(
                                [
                                    html.Span("Generated Cover Letter", className="text-primary fw-bold"),
                                    html.Span(
                                        id="generation-time",
                                        className="ms-2 text-muted",
                                        style={"fontSize": "0.8rem"},
                                    ),
                                ]
                            ),
                            dbc.CardBody(
                                [
                                    dcc.Textarea(
                                        id="generated-cover-letter",
                                        placeholder="Your tailored cover letter will appear here...",
                                        style={
                                            "width": "100%",
                                            "height": "400px",
                                            "borderRadius": "8px",
                                            "padding": "10px",
                                        },
                                        className="mb-3",
                                    ),
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                dbc.Button(
                                                    [html.I(className="fas fa-copy me-2"), "Copy to Clipboard"],
                                                    id="copy-btn",
                                                    color="info",
                                                    className="me-2",
                                                    style=button_style,
                                                ),
                                                width="auto",
                                            ),
                                            dbc.Col(
                                                dbc.Button(
                                                    [html.I(className="fas fa-download me-2"), "Download as Text"],
                                                    id="download-txt-btn",
                                                    color="success",
                                                    className="me-2",
                                                    style=button_style,
                                                ),
                                                width="auto",
                                            ),
                                            dbc.Col(
                                                html.Div(id="copy-status", className="text-success"),
                                                width="auto",
                                            ),
                                        ],
                                        className="g-0",
                                    ),
                                    dcc.Download(id="download-txt"),
                                ]
                            ),
                        ],
                        style=card_style,
                        id="result-card",
                        className="mb-4 mt-3",
                    ),
                    width=12,
                ),
            ],
            id="result-row",
            style={"display": "none"},
        ),
        
        # Footer
        dbc.Row(
            [
                dbc.Col(
                    html.Footer(
                        [
                            html.Hr(),
                            html.P(
                                "© 2023 AI Cover Letter Generator. Powered by Google AI Studio.",
                                className="text-center text-muted",
                            ),
                        ]
                    ),
                    width=12,
                ),
            ]
        ),
        
        # Store components for data
        dcc.Store(id="api-key-store"),
        dcc.Store(id="temp-files"),
        dcc.Store(id="extracted-cover-letter"),
    ],
    fluid=True,
    style={"backgroundColor": "#f8f9fa", "minHeight": "100vh", "padding": "20px"},
)

# Helper functions
def parse_file_contents(contents, filename):
    content_type, content_string = contents.split(",")
    decoded = base64.b64decode(content_string)
    
    try:
        if filename.endswith(".pdf"):
            # Create a temporary file to save the PDF
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                temp_file.write(decoded)
                temp_path = temp_file.name
            
            # Extract text from PDF
            text = ""
            with open(temp_path, "rb") as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for page_num in range(len(pdf_reader.pages)):
                    text += pdf_reader.pages[page_num].extract_text()
            
            # Clean up the temporary file
            os.unlink(temp_path)
            return text
            
        elif filename.endswith(".txt") or filename.endswith(".md") or filename.endswith(".rtf"):
            return decoded.decode("utf-8")
        
        elif filename.endswith(".docx"):
            # For docx files, we'd need the docx2txt library
            # This is a simplified version without docx support
            return "DOCX files are not supported in this simplified example"
        
        else:
            return "Unsupported file format. Please upload a PDF, TXT, or MD file."
    
    except Exception as e:
        return f"Error processing file: {str(e)}"

def extract_pdf_text(contents, filename):
    """Extract text specifically from PDF, with better formatting preservation."""
    content_type, content_string = contents.split(",")
    decoded = base64.b64decode(content_string)
    
    try:
        if filename.endswith(".pdf"):
            # Create a temporary file to save the PDF
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                temp_file.write(decoded)
                temp_path = temp_file.name
            
            # Extract text from PDF with better formatting
            text = ""
            with open(temp_path, "rb") as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for page_num in range(len(pdf_reader.pages)):
                    page_text = pdf_reader.pages[page_num].extract_text()
                    # Clean up common PDF extraction issues
                    page_text = re.sub(r'\s+', ' ', page_text)  # Replace multiple spaces with single space
                    text += page_text + "\n\n"  # Add paragraph breaks between pages
            
            # Clean up the temporary file
            os.unlink(temp_path)
            
            # Additional PDF text cleanup
            text = text.strip()
            # Remove header/footer numbers or emails that might appear on every page
            text = re.sub(r'\n\s*\d+\s*\n', '\n', text)
            text = re.sub(r'\n\s*Page \d+ of \d+\s*\n', '\n', text)
            # Join hyphenated words that were split across lines
            text = re.sub(r'(\w+)-\n(\w+)', r'\1\2', text)
            
            return text
        else:
            return "Please upload a PDF file."
    
    except Exception as e:
        return f"Error processing PDF: {str(e)}"

def extract_job_description_from_url(url):
    """Extract job description content from a URL."""
    try:
        # Validate URL
        parsed_url = urllib.parse.urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            return None, "Invalid URL. Please provide a complete URL including http:// or https://"
        
        # Set headers to mimic a browser request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
        }
        
        # Fetch the webpage
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return None, f"Failed to access the URL. Status code: {response.status_code}"
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.extract()
        
        # Different extraction strategies based on common job board structures
        job_description = ""
        
        # Try to find job description container (common patterns across job sites)
        job_containers = soup.find_all(['div', 'section'], class_=lambda c: c and any(term in str(c).lower() for term in 
                                                              ['job-description', 'description', 'details', 'jobDesc', 'job_des', 
                                                               'jobdetail', 'job-details']))
        
        if job_containers:
            # Use the first matching container
            job_description = job_containers[0].get_text(separator=' ', strip=True)
        else:
            # Fallback: use the main content area
            main_content = soup.find(['main', 'article']) or soup.find('div', {'id': 'content'})
            if main_content:
                job_description = main_content.get_text(separator=' ', strip=True)
            else:
                # Last resort: grab the body text but try to exclude headers, footers
                body = soup.find('body')
                if body:
                    # Skip likely header/nav/footer elements
                    for element in body.find_all(['header', 'nav', 'footer']):
                        element.extract()
                    job_description = body.get_text(separator=' ', strip=True)
        
        # Clean up the extracted text
        job_description = re.sub(r'\s+', ' ', job_description)  # Replace multiple spaces/newlines
        
        # If extraction failed or content too short, return error
        if not job_description or len(job_description) < 100:
            return None, "Could not extract job description from the provided URL. The site may block automated extraction."
        
        return job_description, "Job description extracted successfully!"
    
    except requests.exceptions.Timeout:
        return None, "Request timed out. The website took too long to respond."
    except requests.exceptions.RequestException as e:
        return None, f"Error accessing URL: {str(e)}"
    except Exception as e:
        return None, f"Error extracting job description: {str(e)}"

def generate_adapted_cover_letter(job_description, original_letter, api_key, tone, length, focus):
    # Configure Google AI with the API key
    try:
        genai.configure(api_key=api_key)
        
        # Set up the model
        model = genai.GenerativeModel('gemini-2.5-pro-exp-03-25')
        
        # Create the prompt
        prompt = f"""
        You are a professional cover letter writer. Your task is to adapt an existing cover letter to match a specific job description.
        
        Tone: {tone}
        Length: {length}
        Focus: {focus}
        
        JOB DESCRIPTION:
        {job_description}
        
        ORIGINAL COVER LETTER:
        {original_letter}
        
        Please rewrite the cover letter to:
        1. Match skills and qualifications mentioned in the job description
        2. Maintain the writer's voice and experience
        3. Highlight the most relevant experiences for this specific job
        4. Be well-structured with clear paragraphs
        5. Be persuasive and engaging
        6. Avoid generic content
        7. Keep the letter concise and focused
        
        Format the response as a proper cover letter without any explanations or additional text.
        """
        
        # Generate the adapted cover letter
        response = model.generate_content(prompt)
        return response.text
    
    except Exception as e:
        return f"Error generating cover letter: {str(e)}"

# Callbacks
@app.callback(
    Output("api-key-store", "data"),
    Output("api-key-status", "children"),
    Input("save-api-key", "n_clicks"),
    State("api-key", "value"),
    prevent_initial_call=True,
)
def save_api_key(n_clicks, api_key):
    if not api_key:
        return None, html.Span("Please enter an API key", className="text-danger")
    
    # In a real application, you might want to test the API key here
    return api_key, html.Span("API key saved successfully!", className="text-success")

@app.callback(
    Output("upload-job", "contents"),
    Input("upload-job-btn", "n_clicks"),
    prevent_initial_call=True,
)
def trigger_job_upload(n_clicks):
    return None

@app.callback(
    Output("upload-letter", "contents"),
    Input("upload-letter-btn", "n_clicks"),
    prevent_initial_call=True,
)
def trigger_letter_upload(n_clicks):
    return None

# Combined callback for job description updates
@app.callback(
    Output("job-description", "value"),
    Output("url-extraction-status", "children"),
    [Input("upload-job", "contents"),
     Input("extract-url-btn", "n_clicks")],
    [State("upload-job", "filename"),
     State("job-url", "value")],
    prevent_initial_call=True,
)
def update_job_description(upload_contents, extract_btn, upload_filename, url):
    # Get the ID of the component that triggered the callback
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # Default empty status
    extraction_status = html.Span("", className="")
    
    # Handle file upload trigger
    if trigger_id == "upload-job" and upload_contents is not None:
        parsed_content = parse_file_contents(upload_contents, upload_filename)
        return parsed_content, extraction_status
    
    # Handle URL extraction trigger
    elif trigger_id == "extract-url-btn":
        if not url:
            return "", html.Span("Please enter a URL", className="text-danger")
        
        job_description, message = extract_job_description_from_url(url)
        
        if job_description:
            return job_description, html.Span(message, className="text-success")
        else:
            return "", html.Span(message, className="text-danger")
    
    # Fallback
    raise PreventUpdate

# Combined callback for original cover letter updates (from file upload and PDF extraction)
@app.callback(
    Output("original-cover-letter", "value"),
    Output("cover-letter-tabs", "value"),
    Output("pdf-upload-status", "children"),
    [Input("upload-letter", "contents"),
     Input("pdf-upload", "contents")],
    [State("upload-letter", "filename"),
     State("pdf-upload", "filename")],
    prevent_initial_call=True,
)
def update_cover_letter(upload_contents, pdf_contents, upload_filename, pdf_filename):
    # Get the ID of the component that triggered the callback
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # Default values
    pdf_status = dash.no_update
    tab_value = dash.no_update
    
    # Handle regular file upload
    if trigger_id == "upload-letter" and upload_contents is not None:
        parsed_content = parse_file_contents(upload_contents, upload_filename)
        return parsed_content, tab_value, pdf_status
    
    # Handle PDF upload and extraction
    elif trigger_id == "pdf-upload" and pdf_contents is not None:
        if not pdf_filename or not pdf_filename.lower().endswith('.pdf'):
            pdf_status = html.Div([
                html.I(className="fas fa-exclamation-triangle text-warning me-2"),
                "Please upload a PDF file."
            ])
            return dash.no_update, dash.no_update, pdf_status
        
        extracted_text = extract_pdf_text(pdf_contents, pdf_filename)
        
        if extracted_text and len(extracted_text) > 50:  # Basic validation
            # Store the extracted text and provide a button to use it
            pdf_status = html.Div([
                html.I(className="fas fa-check-circle text-success me-2"),
                f"Successfully extracted cover letter from {pdf_filename}",
                html.Br(),
                html.Button(
                    "Use this text",
                    id="use-pdf-text-btn",
                    className="btn btn-primary btn-sm mt-2",
                    style={"fontSize": "0.8rem"}
                )
            ])
            # Also store the extracted text in the dcc.Store component
            app.clientside_callback(
                """
                function(text) {
                    return text;
                }
                """,
                Output("extracted-cover-letter", "data"),
                [Input("pdf-upload", "contents")],
                [State("extracted-cover-letter", "data")]
            )
            return dash.no_update, dash.no_update, pdf_status
        else:
            pdf_status = html.Div([
                html.I(className="fas fa-exclamation-triangle text-danger me-2"),
                "Could not extract text properly from this PDF."
            ])
            return dash.no_update, dash.no_update, pdf_status
    
    # Fallback
    raise PreventUpdate

# Add a separate callback for the "Use this text" button
@app.callback(
    Output("original-cover-letter", "value", allow_duplicate=True),
    Output("cover-letter-tabs", "value", allow_duplicate=True), 
    Input("use-pdf-text-btn", "n_clicks"),
    State("extracted-cover-letter", "data"),
    prevent_initial_call=True
)
def use_extracted_text(n_clicks, extracted_text):
    if n_clicks is None or not extracted_text:
        raise PreventUpdate
    
    return extracted_text, "manual-cover-tab"

# Keep your existing function to store the PDF text 
@app.callback(
    Output("extracted-cover-letter", "data"),
    Input("pdf-upload", "contents"),
    State("pdf-upload", "filename"),
    prevent_initial_call=True,
)
def store_pdf_text(contents, filename):
    if contents is None or not filename or not filename.lower().endswith('.pdf'):
        raise PreventUpdate
    
    extracted_text = extract_pdf_text(contents, filename)
    
    if extracted_text and len(extracted_text) > 50:  # Basic validation
        return extracted_text
    
    return None

@app.callback(
    Output("loading-indicator", "style"),
    Output("result-row", "style"),
    Output("generated-cover-letter", "value"),
    Output("generation-time", "children"),
    Input("generate-btn", "n_clicks"),
    State("job-description", "value"),
    State("original-cover-letter", "value"),
    State("api-key-store", "data"),
    State("tone-dropdown", "value"),
    State("length-dropdown", "value"),
    State("focus-dropdown", "value"),
    prevent_initial_call=True,
)
def generate_cover_letter(n_clicks, job_desc, original_letter, api_key, tone, length, focus):
    if not n_clicks:
        raise PreventUpdate
    
    if not job_desc or not original_letter:
        return {"display": "none"}, {"display": "none"}, "", ""
    
    if not api_key:
        return {"display": "none"}, {"display": "block"}, "Please save an API key first.", ""
    
    # Show loading indicator
    loading_style = {"display": "block", "textAlign": "center", "paddingTop": "20px", "paddingBottom": "20px"}
    
    # Generate the adapted cover letter
    adapted_letter = generate_adapted_cover_letter(job_desc, original_letter, api_key, tone, length, focus)
    
    # Get current time for timestamp
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    time_display = f"Generated on {current_time}"
    
    # Show results
    result_style = {"display": "block"}
    
    return loading_style, result_style, adapted_letter, time_display

@app.callback(
    Output("copy-status", "children"),
    Input("copy-btn", "n_clicks"),
    State("generated-cover-letter", "value"),
    prevent_initial_call=True,
)
def copy_to_clipboard(n_clicks, text):
    if not text:
        return ""
    
    return html.Span("Copied to clipboard!", className="text-success")

@app.callback(
    Output("download-txt", "data"),
    Input("download-txt-btn", "n_clicks"),
    State("generated-cover-letter", "value"),
    prevent_initial_call=True,
)
def download_text(n_clicks, text):
    if not text:
        raise PreventUpdate
    
    filename = f"Cover_Letter_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    return dict(content=text, filename=filename)

if __name__ == "__main__":
    app.run(debug=True)
