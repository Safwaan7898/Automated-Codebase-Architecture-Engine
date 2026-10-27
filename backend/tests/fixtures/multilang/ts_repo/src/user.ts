import { AuthService } from "./auth";

export class UserService {
  constructor(private auth: AuthService) {}

  getName(): string {
    return "Alice";
  }
}
