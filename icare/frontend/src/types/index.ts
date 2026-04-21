/** Shared frontend DTOs (expand to mirror FastAPI schemas). */

export type UserRole = "patient" | "doctor" | "caregiver";

export interface UserStub {
  id: string;
  email: string;
  name: string;
  role: UserRole;
}
