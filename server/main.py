from fastapi import FastAPI, Query, Request, HTTPException # type: ignore
from pydantic import BaseModel # type: ignore
import google.generativeai as genai # type: ignore
import requests
import uvicorn # type: ignore
import json
from fastapi.middleware.cors import CORSMiddleware # type: ignore
# Initialize FastAPI app
app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure APIs
GENAI_API_KEY = "AIzaSyCN2vzZPonC_ArUIL4PLEh3s0dLyVntrMs"
RAPID_API_KEY = "211a35f372mshf37ae6b9fdd6d0cp181e34jsn3c2994a3ac2f"  
genai.configure(api_key=GENAI_API_KEY)


model=genai.GenerativeModel("gemini-pro")

json_string= '''

        {
            "products": [
                {
                  "name":"Samsung Galaxy S23 Ultra",
                  "key_features": "6.8-inch Dynamic AMOLED 2X display, 5,000mAh battery, Snapdragon 8 Gen 2 processor, 200MP quad-camera system, S Pen support",
                  "price_range": "65,000 - 75,000",
                 "product_photo":"https://m.media-amazon.com/images/I/61K1Fz5LxvL._AC_UY654_FMwebp_QL65_.jpg"
                },
                {
                  "name": "Samsung GalaxyA54",
                  "key_features": "6.4-inch AMOLED display, 5,000mAh battery, Exynos 1280 processor, 50MP triple-camera system, IP67 water resistance",
                  "price_range": "35,000 - 45,000"
                  "product_photo":"https://m.media-amazon.com/images/I/61s0ZzwzSCL._AC_UY654_FMwebp_QL65_.jpg"
                },
                {
                  "name": "Samsung Galaxy M53",
                  "key_features": "6.7-inch Super AMOLED Plus display, 5,000mAh battery, MediaTek Dimensity 900 processor, 108MP triple-camera system",
                  "price_range": "25,000 - 35,000"
                  "product_photo":"https://m.media-amazon.com/images/I/812woqv69CL._AC_UY654_FMwebp_QL65_.jpg"
                },
                {
                  "name": "Samsung Galaxy A73",
                  "key_features": "6.7-inch Super AMOLED Plus display, 5,000mAh battery, Snapdragon 778G processor, 108MP quad-camera system, IP67 water resistance",
                  "price_range": "45,000 - 55,000"
                  "product_photo":"https://m.media-amazon.com/images/I/51m744UUjYL._AC_UY654_FMwebp_QL65_.jpg"
                }
            ]
        }
'''

def generate_questions(category: str):
    """
    Generate 5 questions based on the product category using Google Generative AI (Gemini).
    """
    try:
        prompt = (
            f"Ask 5 distinct questions to help narrow down my preferences "
            f"for purchasing a {category}, focusing on budget, features, brand preferences i.e. which brand I prefer, "
            f"screen size, and other important factors. "
            f"The questions should be in a conversational style, suitable for a chatbot."
        )
        # Generate content using the model
        response = model.generate_content(prompt)
        # Extract and clean questions
        questions = [q.strip() for q in response.text.split("\n") if q.strip()]
        formatted_questions = [q.replace("\"", "") for q in questions]

        return formatted_questions
    except Exception as e:
        raise ValueError(f"Error generating questions: {str(e)}")

@app.get("/questions")
def generate_questions_endpoint(category: str = Query(..., description="The product category to generate questions for")):
    """
    API Endpoint to generate questions for a given category.
    """
    print(category)
    try:
        questions = generate_questions(category)
        print(questions)
        return {"category": category, "questions": questions}
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/test")
def test():
    return {"message": "API is working!"}


@app.post("/getProducts")
async def get_products(response: Request):

    user_responses = (await response.json())
    prompt = (
        "Based on the following user preferences, recommend 4 products:\n"
        f"{user_responses}\n"
        "The recommendations should include product names, key features, and price ranges. "
        f"The products should be relevant to the user's needs and budget and in new line give the product ASIN number separately and are easily available on amazon india and price range should be in the user budget if no recommendation is found say no product is available, return respone in form of json or dict so it can easily be parse in format {json_string}"
    )
    products = model.generate_content(prompt, stream=True)
    products.resolve()
    products_json = products.text if hasattr(products, 'text') else str(products)
        
    products_dict = json.loads(products_json)
        
    return products_dict
   

def fetch_reviews(asin):
    url = "https://real-time-amazon-data.p.rapidapi.com/product-reviews"
    querystring = {
        "asin": asin,
        "country": "IN",  # Update to your target country
        "sort_by": "TOP_REVIEWS",
        "star_rating": "ALL",
        "verified_purchases_only": "false",
        "images_or_videos_only": "false",
        "current_format_only": "false",
        "page": "1"
    }

    headers = {
        "x-rapidapi-key": RAPID_API_KEY,
        "x-rapidapi-host": "real-time-amazon-data.p.rapidapi.com"
        }

    response = requests.get(url, headers=headers, params=querystring)
    data = response.json()
    if(response.status_code==200):
      reviews_data = {
          "asin": data.get("data", {}).get("asin"),
          "reviews": data.get("data", {}).get("reviews", [])
      }
      return reviews_data
    else:
        print("Error: No reviews found or invalid ASIN.")

    return {}

def get_reviews_by_asin(asin_details):
    review_list={}
    for product_name, details in asin_details.items():
        asin=(details["asin"])
        print(asin)
        data = fetch_reviews(asin)
        result = [review['review_comment'] for review in data['reviews']]
        review_list[product_name]=result
    return review_list


def analyze_reviews(review_data):
    # Format the review data into a JSON-like string
    review_data_str = "\n".join(
        [f'"{asin}": {reviews}' for asin, reviews in review_data.items()]
    )

    # Prompt to summarize and analyze
    prompt = (
        f"You are an AI assistant tasked with analyzing and summarizing customer reviews for products. "
        f"Given the following review data in dictionary format, perform the following tasks:\n\n"
        f"1. Summarize the overall sentiment and key themes of the reviews for each product.\n"
        f"2. Assign a score out of 10 for each product's reviews, representing how positively the reviewers perceive the product. "
        f"Use a precision of up to 5 decimal places, with a higher score indicating better feedback.\n"
        f"3. Identify the product with the highest score and recommend it as the best product.\n"
        f"4. Provide a detailed summary of why this product is the best, focusing on its highlighted strengths from the reviews.\n\n"
        f"### Input:\n{{\n{review_data_str}\n}}\n\n"
        f"### Output:\nProvide the output in the following format:\n\n"
        f'{{\n'
        f'    "summary": {{\n'
        f'        "<asin>": {{\n'
        f'            "review_summary": "<summarized sentiment and themes>",\n'
        f'            "score": <score out of 10 (precision 5 decimal places)>\n'
        f'        }}\n'
        f'    }},\n'
        f'    "best_product": {{\n'
        f'        "asin": "<asin of the best product>",\n'
        f'        "reason": "<why this product stands out based on reviews>",\n'
        f'        "review_summary": "<summary of the reviews of the best product>"\n'
        f'    }}\n'
        f'}}'
    )

    # Generate response from the model
    response = model.generate_content(prompt)

    # Parse and return the result
    return response.text

def fetch_product_details(product_names):
    asin_details = {}
    for name in product_names:
        product = get_electronic_products(name)
        if product:
            asin_details[name] = {
                "asin": product["asin"],
                "price": product["price"],
                "rating": product["rating"],
                "num_ratings": product["num_ratings"],
                "url": product["url"],
                "product_photo": product["product_photo"],
            }
        else:
            asin_details[name] = "No product found"
    return asin_details


def get_electronic_products(query):
    url = "https://real-time-amazon-data.p.rapidapi.com/search"
    querystring = {
        "query": query,
        "page": "1",
        "country": "IN",
        "sort_by": "RELEVANCE",
        "product_condition": "ALL",
        "is_prime": "false"
    }

    headers = {
        "x-rapidapi-key": RAPID_API_KEY,
        "x-rapidapi-host": "real-time-amazon-data.p.rapidapi.com"
    }

    response = requests.get(url, headers=headers, params=querystring)
    product_data = response.json()

    if "data" in product_data and "products" in product_data["data"]:
        filtered_products = []

        for product in product_data["data"]["products"]:
            if isinstance(product, dict):
                filtered_products.append({
                    "name": product.get("product_title", ""),
                    "asin": product.get("asin", ""),
                    "price": product.get("product_price", "N/A"),
                    "rating": product.get("product_star_rating", "N/A"),
                    "num_ratings": product.get("product_num_ratings", 0),
                    "url": product.get("product_url", ""),
                    "product_photo": product.get("product_photo", "")  # Correct the key here
                })

        return filtered_products[0] if filtered_products else []
    else:
        print("Error: Invalid product data")
        return []


@app.post("/getAsin")
async def get_asin(response: Request):
    try:
        user_responses = await response.json()
        product_names = user_responses.get("products", [])
        user_budget = user_responses.get("budget", None)  # Accept budget if provided
        if not product_names:
            raise HTTPException(status_code=400, detail="No products provided in the request.")

        # Fetch ASIN details
        asin_details = fetch_product_details(product_names)
        return {"asin_details": asin_details}
    except Exception as e:
        return {"error": str(e)}


@app.post("/getReviews")
async def get_reviews(response: Request):
    try:
        user_responses = await response.json()
        
        # Filter valid ASINs
        valid_asins = {key: value for key, value in user_responses.items() if value != "No product found"}
        
        if not valid_asins:
            raise HTTPException(status_code=400, detail="No valid ASINs provided.")
        
        # Fetch reviews for valid ASINs
        review_data = get_reviews_by_asin(valid_asins)
        
        # Analyze reviews
        analysis_result = analyze_reviews(review_data)
        
        # Process analysis result
        if isinstance(analysis_result, str):
            result_json = analysis_result
        elif hasattr(analysis_result, 'text'):
            result_json = analysis_result.text
        else:
            result_json = json.dumps(analysis_result)
        
        print("Result JSON:", result_json)
        
        # Parse the JSON string
        parsed_result = json.loads(result_json)
        return parsed_result
    
    except json.JSONDecodeError as e:
        print("JSON Decode Error:", str(e))
        raise HTTPException(status_code=500, detail="Failed to parse analysis result.")
    except Exception as e:
        print("Error:", str(e))
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app)