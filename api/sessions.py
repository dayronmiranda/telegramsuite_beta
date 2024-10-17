from fastapi import APIRouter, HTTPException, Form
from services.telegram_client import create_session, close_session, sign_in_with_code
from database.mongodb import get_db
from utils.logging import logger
from bson import ObjectId

router = APIRouter()

@router.post("/")
async def register_session(phone: str = Form(...), api_id: int = Form(...), api_hash: str = Form(...)):
    db = get_db()
    client = await create_session(phone, api_id, api_hash)
    try:
        if not await client.is_user_authorized():
            # Almacenar la sesión con estado "pending"
            session_document = {
                "phone": phone,
                "api_id": api_id,
                "api_hash": api_hash,
                "status": "pending",
                "session_data": client.session.save()
            }
            session_id = await db.sessions.insert_one(session_document)
            await client.send_code_request(phone)
            return {"message": "Verification code sent. Use the verify_code endpoint.", "session_id": str(session_id.inserted_id)}
        
        # Si ya está autorizado, almacenar la sesión como "active"
        session_document = {
            "phone": phone,
            "api_id": api_id,
            "api_hash": api_hash,
            "status": "active",
            "session_data": client.session.save()
        }
        session_id = await db.sessions.insert_one(session_document)
        logger.info(f"Session registered successfully for {phone}")
        return {"message": "Session registered successfully.", "session_id": str(session_id.inserted_id)}
    except Exception as e:
        logger.error(f"Error registering session: {str(e)}")
        raise HTTPException(status_code=500, detail="Error registering session.")
    finally:
        await close_session(client)

@router.post("/verify_code")
async def verify_code(session_id: str = Form(...), code: str = Form(...)):
    db = get_db()
    session_data = await db.sessions.find_one({"_id": ObjectId(session_id)})
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found. Register the session first.")
    
    if session_data["status"] != "pending":
        raise HTTPException(status_code=400, detail="This session is not waiting for verification.")
    
    client = await create_session(session_data["phone"], session_data["api_id"], session_data["api_hash"])
    try:
        await sign_in_with_code(client, session_data["phone"], code)
        # Actualizar el estado de la sesión a "active"
        await db.sessions.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": {"status": "active", "session_data": client.session.save()}}
        )
        logger.info(f"Verification code accepted for {session_data['phone']}")
        return {"message": "Verification code accepted. Session is now active."}
    except Exception as e:
        logger.error(f"Error verifying code: {str(e)}")
        raise HTTPException(status_code=500, detail="Error verifying code.")
    finally:
        await close_session(client)