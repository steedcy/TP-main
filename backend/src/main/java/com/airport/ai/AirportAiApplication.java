package com.airport.ai;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class AirportAiApplication {

    public static void main(String[] args) {
        SpringApplication.run(AirportAiApplication.class, args);
    }
}
