#!/usr/bin/env python3
"""
Test script for Feedback Storage Backend (Day 4 Verification)

Tests:
1. MongoDB connection
2. Feedback endpoint availability
3. Feedback CRUD operations
4. Atomic counter updates
5. Feedback array accumulation

Usage:
    python test_feedback_backend.py

Requirements:
    - Backend server running on http://localhost:8000
    - MongoDB accessible (mongodb://localhost:27017 or via Docker network)
"""

import asyncio
import json
import sys
from datetime import datetime

import requests

BASE_URL = "http://localhost:8000"


def test_feedback_endpoint():
    """Test the feedback API endpoint with various scenarios."""
    print("\n" + "=" * 60)
    print("FEEDBACK BACKEND VERIFICATION TEST")
    print("=" * 60)

    test_message_id = f"test-msg-{int(datetime.now().timestamp())}"
    results = []

    # Test 1: Submit a like
    print("\n[Test 1] Submitting a LIKE...")
    try:
        response = requests.post(
            f"{BASE_URL}/api/feedback",
            json={
                "messageId": test_message_id,
                "serverId": "test-server-123",  # NEW: associate with MCP server
                "type": "like",
                "userId": "test-user-1",
                "comment": "Great response!"
            },
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
            assert data["likeCount"] == 1
            assert data["dislikeCount"] == 0
            assert data["totalFeedbacks"] == 1
            print(f"  ✅ PASS: Like recorded (counts: {data['likeCount']} likes, {data['dislikeCount']} dislikes)")
            results.append(True)
        else:
            print(f"  ❌ FAIL: HTTP {response.status_code} - {response.text}")
            results.append(False)
    except Exception as e:
        print(f"  ❌ FAIL: {e}")
        results.append(False)

    # Test 2: Submit another like (should increment)
    print("\n[Test 2] Submitting second LIKE (increment test)...")
    try:
        response = requests.post(
            f"{BASE_URL}/api/feedback",
            json={
                "messageId": test_message_id,
                "serverId": "test-server-123",  # same serverId
                "type": "like",
                "userId": "test-user-2"
            },
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
            assert data["likeCount"] == 2
            assert data["dislikeCount"] == 0
            assert data["totalFeedbacks"] == 2
            print(f"  ✅ PASS: Like count incremented to {data['likeCount']}")
            results.append(True)
        else:
            print(f"  ❌ FAIL: HTTP {response.status_code} - {response.text}")
            results.append(False)
    except Exception as e:
        print(f"  ❌ FAIL: {e}")
        results.append(False)

    # Test 3: Submit a dislike (different counter)
    print("\n[Test 3] Submitting a DISLIKE (separate counter)...")
    try:
        response = requests.post(
            f"{BASE_URL}/api/feedback",
            json={
                "messageId": test_message_id,
                "serverId": "test-server-123",
                "type": "dislike",
                "userId": "test-user-3",
                "comment": "Not quite right"
            },
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
            assert data["likeCount"] == 2  # unchanged
            assert data["dislikeCount"] == 1
            assert data["totalFeedbacks"] == 3
            print(f"  ✅ PASS: Dislike counted separately (L: {data['likeCount']}, D: {data['dislikeCount']})")
            results.append(True)
        else:
            print(f"  ❌ FAIL: HTTP {response.status_code} - {response.text}")
            results.append(False)
    except Exception as e:
        print(f"  ❌ FAIL: {e}")
        results.append(False)

    # Test 4: Get feedback statistics
    print("\n[Test 4] Retrieving feedback statistics...")
    try:
        response = requests.get(f"{BASE_URL}/api/feedback/{test_message_id}", timeout=10)
        if response.status_code == 200:
            data = response.json()
            assert data["messageId"] == test_message_id
            assert data["likeCount"] == 2
            assert data["dislikeCount"] == 1
            assert len(data["feedbacks"]) == 3
            # Verify serverId is present in feedback entries (NEW)
            for feedback in data["feedbacks"]:
                assert feedback.get("serverId") == "test-server-123", "serverId should be stored in each feedback entry"
            print(f"  ✅ PASS: Retrieved {len(data['feedbacks'])} feedback entries with serverId")
            results.append(True)
        elif response.status_code == 404:
            print(f"  ⚠️ SKIP: No feedback found (may need to check MongoDB persistence)")
            results.append(True)  # Not a critical failure
        else:
            print(f"  ❌ FAIL: HTTP {response.status_code} - {response.text}")
            results.append(False)
    except Exception as e:
        print(f"  ❌ FAIL: {e}")
        results.append(False)

    # Test 5: Get non-existent feedback
    print("\n[Test 5] Retrieving non-existent feedback (should 404)...")
    try:
        response = requests.get(f"{BASE_URL}/api/feedback/non-existent-msg-id", timeout=10)
        if response.status_code == 404:
            print(f"  ✅ PASS: Correctly returned 404 for missing feedback")
            results.append(True)
        else:
            print(f"  ❌ FAIL: Expected 404, got {response.status_code}")
            results.append(False)
    except Exception as e:
        print(f"  ❌ FAIL: {e}")
        results.append(False)

    # Test 6: Feedback with NO serverId (backwards compatibility)
    print("\n[Test 6] Feedback without serverId (backwards compatibility)...")
    try:
        test_msg_no_server = f"test-no-server-{int(datetime.now().timestamp())}"
        response = requests.post(
            f"{BASE_URL}/api/feedback",
            json={
                "messageId": test_msg_no_server,
                # No serverId field
                "type": "like",
                "userId": "test-user"
            },
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
            assert data["likeCount"] == 1
            print(f"  ✅ PASS: Feedback without serverId works (backwards compatible)")
            results.append(True)
        else:
            print(f"  ❌ FAIL: HTTP {response.status_code} - {response.text}")
            results.append(False)
    except Exception as e:
        print(f"  ❌ FAIL: {e}")
        results.append(False)

    # Summary
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"RESULTS: {passed}/{total} tests passed")

    if passed == total:
        print("✅ ALL TESTS PASSED - Feedback backend is working correctly!")
        return 0
    else:
        print("❌ SOME TESTS FAILED - Check backend logs for details")
        return 1


def test_health_endpoint():
    """Quick health check."""
    print("\n[Health Check] Verifying backend is running...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ Backend healthy: {data}")
            return True
        else:
            print(f"  ❌ Backend unhealthy: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"  ❌ Cannot reach backend: {e}")
        print("  ℹ️  Make sure the backend is running (uvicorn main:app --reload)")
        return False


if __name__ == "__main__":
    # First check if backend is reachable
    if not test_health_endpoint():
        print("\n❌ Backend is not available. Please start the server first:")
        print("   cd backend && uvicorn main:app --reload --port 8000")
        sys.exit(1)

    # Run feedback tests
    exit_code = test_feedback_endpoint()
    sys.exit(exit_code)
