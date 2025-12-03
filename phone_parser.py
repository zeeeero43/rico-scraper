"""
Phone number parser for Cuban phone number formats
"""

import re
from typing import List, Set

class PhoneNumberParser:
    """Parser for extracting and validating Cuban phone numbers"""
    
    def __init__(self):
        # Cuban phone number patterns
        self.patterns = [
            # +53 XXXX XXXX format
            r'\+53\s*[5-9]\d{3}\s*\d{4}',
            # 53XXXXXXXX format
            r'53[5-9]\d{7}',
            # XXXX-XXXX format (local Cuban numbers)
            r'[5-9]\d{3}-\d{4}',
            # (XXX) XXX-XXXX format
            r'\([5-9]\d{2}\)\s*\d{3}-\d{4}',
            # XXXXXXXX format (8 digits starting with 5-9)
            r'[5-9]\d{7}',
            # XXX-XXXX format (7 digits with dash)
            r'[5-9]\d{2}-\d{4}',
            # +53-XXXX-XXXX format
            r'\+53-[5-9]\d{3}-\d{4}',
            # 53 XXXX XXXX format (with space)
            r'53\s+[5-9]\d{3}\s+\d{4}',
            # (53) XXXX XXXX format
            r'\(53\)\s*[5-9]\d{3}\s*\d{4}'
        ]
        
        # Compile patterns for better performance
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.patterns]
        
    def extract_phone_numbers(self, text: str) -> List[str]:
        """Extract all phone numbers from text"""
        if not text:
            return []
            
        found_numbers = set()
        
        # Apply each pattern
        for pattern in self.compiled_patterns:
            matches = pattern.findall(text)
            for match in matches:
                # Clean up the number
                cleaned = self.clean_phone_number(match)
                if self.is_valid_cuban_number(cleaned):
                    found_numbers.add(cleaned)
        
        # Also look for numbers in common formats without strict patterns
        # This catches variations that might not match exact patterns
        loose_pattern = r'(?:\+?53[-.\s]?)?[5-9]\d{2,3}[-.\s]?\d{3,4}'
        loose_matches = re.findall(loose_pattern, text)
        
        for match in loose_matches:
            cleaned = self.clean_phone_number(match)
            if self.is_valid_cuban_number(cleaned):
                found_numbers.add(cleaned)
        
        return sorted(list(found_numbers))
    
    def clean_phone_number(self, phone: str) -> str:
        """Clean and normalize phone number"""
        if not phone:
            return ""
            
        # Remove all non-digit characters except +
        cleaned = re.sub(r'[^\d+]', '', phone)
        
        # Handle different formats
        if cleaned.startswith('+53'):
            return cleaned
        elif cleaned.startswith('53') and len(cleaned) >= 10:
            return '+' + cleaned
        elif len(cleaned) == 8 and cleaned[0] in '56789':
            return '+53' + cleaned
        elif len(cleaned) == 7 and cleaned[0] in '56789':
            return '+535' + cleaned
        
        return cleaned
    
    def is_valid_cuban_number(self, phone: str) -> bool:
        """Validate if number follows Cuban mobile number format"""
        if not phone:
            return False
            
        # Remove + and spaces for validation
        digits_only = re.sub(r'[^\d]', '', phone)
        
        # Cuban mobile numbers should:
        # - Start with 53 (country code)
        # - Followed by 5-9 (mobile prefix)
        # - Total of 10 digits (53 + 8 digits)
        
        if len(digits_only) == 10 and digits_only.startswith('53'):
            # Third digit should be 5-9 for mobile numbers
            if digits_only[2] in '56789':
                return True
        
        # Also accept 8-digit numbers starting with 5-9 (local format)
        elif len(digits_only) == 8 and digits_only[0] in '56789':
            return True
            
        # Accept 7-digit numbers starting with 5-9 (older format)
        elif len(digits_only) == 7 and digits_only[0] in '56789':
            return True
        
        return False
    
    def format_phone_number(self, phone: str) -> str:
        """Format phone number in standard +53 XXXX XXXX format"""
        cleaned = self.clean_phone_number(phone)
        
        if not self.is_valid_cuban_number(cleaned):
            return phone  # Return original if invalid
        
        digits_only = re.sub(r'[^\d]', '', cleaned)
        
        if len(digits_only) == 10 and digits_only.startswith('53'):
            # Format as +53 XXXX XXXX
            return f"+53 {digits_only[2:6]} {digits_only[6:]}"
        elif len(digits_only) == 8:
            # Add country code and format
            return f"+53 {digits_only[:4]} {digits_only[4:]}"
        elif len(digits_only) == 7:
            # Add country code and format with leading 5
            return f"+53 5{digits_only[:3]} {digits_only[3:]}"
        
        return phone
    
    def validate_and_format_numbers(self, numbers: List[str]) -> List[str]:
        """Validate and format a list of phone numbers"""
        formatted_numbers = []
        
        for number in numbers:
            if self.is_valid_cuban_number(number):
                formatted = self.format_phone_number(number)
                if formatted not in formatted_numbers:
                    formatted_numbers.append(formatted)
        
        return formatted_numbers
