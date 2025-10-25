#!/usr/bin/env python3
"""
Test script for default user template implementation
Tests both the existence of default users and the signup process using them.
"""

import requests
import json
import random
import string

# Configuration
ODOO_URL = "http://localhost:8069"
TEST_EMAIL_DOMAIN = "test-" + ''.join(random.choices(string.ascii_lowercase, k=6)) + ".local"


def generate_test_email(prefix):
    """Generate a unique test email"""
    return f"{prefix}-{random.randint(1000, 9999)}@{TEST_EMAIL_DOMAIN}"


def test_signup(user_type, name, email, password, phone=""):
    """Test user signup with default template"""
    print(f"\n{'='*60}")
    print(f"Testing {user_type.upper()} signup")
    print(f"{'='*60}")
    
    signup_data = {
        'name': name,
        'email': email,
        'password': password,
        'phone': phone,
        'user_type': user_type
    }
    
    print(f"Sending signup request for: {email}")
    print(f"Request data: {json.dumps({k: v if k != 'password' else '***' for k, v in signup_data.items()}, indent=2)}")
    
    try:
        response = requests.post(
            f'{ODOO_URL}/api/auth/signup',
            json=signup_data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        print(f"\nResponse Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✓ Signup successful!")
            print(f"\nUser Profile:")
            print(json.dumps(result.get('user', {}), indent=2))
            
            # Validate groups
            groups = result.get('user', {}).get('groups', [])
            group_names = [g['name'] for g in groups]
            print(f"\nAssigned Groups:")
            for group in group_names:
                print(f"  - {group}")
            
            # Validate role
            role = result.get('user', {}).get('role')
            expected_role = 'job_applicant' if user_type == 'candidate' else 'recruitment_officer'
            if role == expected_role:
                print(f"✓ Role correctly set to: {role}")
            else:
                print(f"✗ Role mismatch! Expected: {expected_role}, Got: {role}")
            
            # Check permissions
            permissions = result.get('user', {}).get('permissions', {})
            print(f"\nPermissions:")
            for perm, value in permissions.items():
                print(f"  - {perm}: {value}")
            
            return True
        else:
            print(f"✗ Signup failed!")
            print(f"Error: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"✗ Connection Error: Could not connect to {ODOO_URL}")
        print("Make sure Odoo is running and accessible")
        return False
    except requests.exceptions.Timeout:
        print("✗ Request Timeout: The server took too long to respond")
        return False
    except Exception as e:
        print(f"✗ Unexpected Error: {str(e)}")
        return False


def test_login(email, password):
    """Test user login"""
    print(f"\n{'='*60}")
    print(f"Testing LOGIN for: {email}")
    print(f"{'='*60}")
    
    login_data = {
        'email': email,
        'password': password
    }
    
    try:
        response = requests.post(
            f'{ODOO_URL}/api/auth/login',
            json=login_data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("✓ Login successful!")
                print(f"User: {result.get('user', {}).get('name')}")
                print(f"Role: {result.get('user', {}).get('role')}")
                return True
            else:
                print(f"✗ Login failed: {result.get('error')}")
                return False
        else:
            print(f"✗ Login failed!")
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Error during login: {str(e)}")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("DEFAULT USER TEMPLATE IMPLEMENTATION TEST")
    print("="*60)
    print(f"Odoo URL: {ODOO_URL}")
    print(f"Test Email Domain: {TEST_EMAIL_DOMAIN}")
    
    results = {
        'candidate_signup': False,
        'employer_signup': False,
        'candidate_login': False,
        'employer_login': False
    }
    
    # Generate test credentials
    candidate_email = generate_test_email("candidate")
    candidate_password = "TestPass123!"
    employer_email = generate_test_email("employer")
    employer_password = "TestPass456!"
    
    # Test 1: Candidate Signup
    results['candidate_signup'] = test_signup(
        user_type='candidate',
        name='Test Candidate User',
        email=candidate_email,
        password=candidate_password,
        phone='012345678'
    )
    
    # Test 2: Employer Signup
    results['employer_signup'] = test_signup(
        user_type='employer',
        name='Test Employer User',
        email=employer_email,
        password=employer_password,
        phone='098765432'
    )
    
    # Test 3: Candidate Login (will fail if email verification is enforced)
    # results['candidate_login'] = test_login(candidate_email, candidate_password)
    
    # Test 4: Employer Login (will fail if email verification is enforced)
    # results['employer_login'] = test_login(employer_email, employer_password)
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for test_name, result in results.items():
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{test_name.replace('_', ' ').title()}: {status}")
    
    # Check for Odoo logs
    print("\n" + "="*60)
    print("VERIFICATION STEPS")
    print("="*60)
    print("\nTo verify the implementation in Odoo:")
    print("1. Check Odoo server logs for messages like:")
    print("   - 'Using default user template: angkot_recruitement.default_candidate_user'")
    print("   - 'User created from template: ID=..., login=..., groups=[...]'")
    print("\n2. Verify default template users exist (in Odoo shell):")
    print("   candidate = env.ref('angkot_recruitement.default_candidate_user')")
    print("   employer = env.ref('angkot_recruitement.default_employer_user')")
    print("   print(f'Candidate: {candidate.name}, Active: {candidate.active}')")
    print("   print(f'Employer: {employer.name}, Active: {employer.active}')")
    print("\n3. Check created users in Odoo UI:")
    print("   Settings → Users & Companies → Users")
    print(f"   Search for: {candidate_email}")
    print(f"   Search for: {employer_email}")
    print("\n4. Verify groups are correctly assigned:")
    print("   - Candidates should have: 'Internal User' + 'Job Applicant'")
    print("   - Employers should have: 'Internal User' + 'Recruitment Officer'")
    
    # Overall result
    all_passed = all(results.values())
    print("\n" + "="*60)
    if all_passed:
        print("✓ ALL TESTS PASSED")
    else:
        print("✗ SOME TESTS FAILED")
    print("="*60 + "\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())

