async def test_mongodb_connection():
    """Test MongoDB connection."""
    from app.database import initialize_database
    
    try:
        # Initialize database
        initialized = await initialize_database()
        
        if initialized:
            print("MongoDB connection successful!")
            return True
        else:
            print("MongoDB connection failed")
            return False
    except Exception as e:
        print(f"Error connecting to MongoDB: {str(e)}")
        return False

# Run the test
if __name__ == "__main__":
    import asyncio
    asyncio.run(test_mongodb_connection())