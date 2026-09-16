from typing import List
from app.schemas.compliance import ComplianceControlSchema

COMPLIANCE_CATALOG: List[ComplianceControlSchema] = [
    # SOC 2 Type II
    ComplianceControlSchema(
        framework="SOC 2 Type II",
        control_id="CC1.1",
        control_title="COSO Principle 1: Integrity and Ethical Values",
        control_description="The entity demonstrates a commitment to integrity and ethical values.",
        required_evidence="Code of conduct, ethics policy, or similar commitment to integrity.",
        category="Security"
    ),
    ComplianceControlSchema(
        framework="SOC 2 Type II",
        control_id="CC6.1",
        control_title="Logical Access Security",
        control_description="The entity implements logical access security software, infrastructure, and architectures over protected information assets to protect them from security events.",
        required_evidence="Passwords, MFA, Role-Based Access Control, single sign-on (SSO), least privilege principles.",
        category="Security"
    ),
    # ISO 27001
    ComplianceControlSchema(
        framework="ISO 27001",
        control_id="A.8.1.1",
        control_title="Inventory of assets",
        control_description="Information, other assets associated with information and information processing facilities shall be identified and an inventory of these assets shall be drawn up and maintained.",
        required_evidence="Mention of asset inventory, data mapping, or maintaining a record of processing activities.",
        category="Security"
    ),
    ComplianceControlSchema(
        framework="ISO 27001",
        control_id="A.9.2.1",
        control_title="User registration and de-registration",
        control_description="A formal user registration and de-registration process shall be implemented to enable assignment of access rights.",
        required_evidence="Provisioning and de-provisioning procedures, access reviews, user lifecycle management.",
        category="Security"
    ),
    # GDPR
    ComplianceControlSchema(
        framework="GDPR",
        control_id="Art. 32",
        control_title="Security of processing",
        control_description="Taking into account the state of the art, the costs of implementation and the nature, scope, context and purposes of processing as well as the risk of varying likelihood and severity for the rights and freedoms of natural persons, the controller and the processor shall implement appropriate technical and organisational measures to ensure a level of security appropriate to the risk.",
        required_evidence="Encryption, pseudonymisation, ability to ensure ongoing confidentiality, integrity, availability and resilience.",
        category="Privacy"
    ),
    ComplianceControlSchema(
        framework="GDPR",
        control_id="Art. 17",
        control_title="Right to erasure ('right to be forgotten')",
        control_description="The data subject shall have the right to obtain from the controller the erasure of personal data concerning him or her without undue delay.",
        required_evidence="Data deletion policies, right to be forgotten mechanisms, retention schedules.",
        category="Privacy"
    ),
    # HIPAA
    ComplianceControlSchema(
        framework="HIPAA",
        control_id="164.312(a)(1)",
        control_title="Access Control",
        control_description="Implement technical policies and procedures for electronic information systems that maintain electronic protected health information to allow access only to those persons or software programs that have been granted access rights as specified in §164.308(a)(4).",
        required_evidence="Unique user identification, emergency access procedure, automatic logoff, encryption and decryption.",
        category="Security"
    ),
    ComplianceControlSchema(
        framework="HIPAA",
        control_id="164.312(e)(1)",
        control_title="Transmission Security",
        control_description="Implement technical security measures to guard against unauthorized access to electronic protected health information that is being transmitted over an electronic communications network.",
        required_evidence="Integrity controls and encryption in transit (e.g., TLS, HTTPS).",
        category="Security"
    ),
    # NIST SP 800-53
    ComplianceControlSchema(
        framework="NIST SP 800-53",
        control_id="AC-2",
        control_title="Account Management",
        control_description="The organization manages information system accounts, including establishing, activating, modifying, reviewing, disabling, and removing accounts.",
        required_evidence="Account provisioning, deprovisioning, access reviews, role-based access control.",
        category="Security"
    ),
    ComplianceControlSchema(
        framework="NIST SP 800-53",
        control_id="SC-8",
        control_title="Transmission Confidentiality and Integrity",
        control_description="The information system protects the confidentiality and integrity of transmitted information.",
        required_evidence="Encryption in transit, HTTPS, TLS, VPNs.",
        category="Security"
    ),
]

def get_catalog_by_framework(framework: str) -> List[ComplianceControlSchema]:
    return [c for c in COMPLIANCE_CATALOG if c.framework == framework]
