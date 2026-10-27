import { UserService } from "./user";

export class AuthService {
  constructor(private user: UserService) {}

  validate(): boolean {
    return true;
  }
}
