package main

import (
	"strava-killer/rest"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
)

func main() {

	r := gin.New()
	corsConfig := cors.DefaultConfig() //TODO: fix cors
	corsConfig.AllowAllOrigins = true

	r.Use(
		cors.New(corsConfig),
		gin.Recovery(),
	)

	h := rest.NewHandler()
	r.POST("/generate-single", h.HandleGenerateFileSingleMarker)

	r.Run() // listen and serve on 0.0.0.0:8080
}
