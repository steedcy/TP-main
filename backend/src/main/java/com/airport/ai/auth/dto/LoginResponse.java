package com.airport.ai.auth.dto;

public class LoginResponse {
    private String token;
    private String tokenType = "Bearer";
    private long expiresIn;
    private UserView user;

    public static class UserView {
        private Long id;
        private String username;
        private String realName;
        private String role;

        public UserView(Long id, String username, String realName, String role) {
            this.id = id;
            this.username = username;
            this.realName = realName;
            this.role = role;
        }
        public Long getId() { return id; }
        public String getUsername() { return username; }
        public String getRealName() { return realName; }
        public String getRole() { return role; }
    }

    public LoginResponse(String token, long expiresIn, UserView user) {
        this.token = token;
        this.expiresIn = expiresIn;
        this.user = user;
    }

    public String getToken() { return token; }
    public String getTokenType() { return tokenType; }
    public long getExpiresIn() { return expiresIn; }
    public UserView getUser() { return user; }
}
