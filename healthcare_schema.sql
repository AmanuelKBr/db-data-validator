-- ============================================================
-- HealthcareDemo Database
-- Single-table schema for Kaggle Healthcare Dataset
-- 55,500 patient records
-- ============================================================

USE master;
GO

IF EXISTS (SELECT name FROM sys.databases WHERE name = 'HealthcareDemo')
    DROP DATABASE HealthcareDemo;
GO

CREATE DATABASE HealthcareDemo;
GO

USE HealthcareDemo;
GO

CREATE TABLE dbo.PatientRecords (
    PatientID           INT             IDENTITY(1,1)   PRIMARY KEY,
    Name                NVARCHAR(150)   NULL,
    Age                 INT             NULL,
    Gender              NVARCHAR(20)    NULL,
    BloodType           NVARCHAR(5)     NULL,
    MedicalCondition    NVARCHAR(100)   NULL,
    DateOfAdmission     DATE            NULL,
    Doctor              NVARCHAR(150)   NULL,
    Hospital            NVARCHAR(200)   NULL,
    InsuranceProvider   NVARCHAR(100)   NULL,
    BillingAmount       DECIMAL(12,2)   NULL,
    RoomNumber          INT             NULL,
    AdmissionType       NVARCHAR(50)    NULL,
    DischargeDate       DATE            NULL,
    Medication          NVARCHAR(100)   NULL,
    TestResults         NVARCHAR(50)    NULL,
    CreatedAt           DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME()
);
GO

PRINT 'HealthcareDemo database and PatientRecords table created successfully.';
GO